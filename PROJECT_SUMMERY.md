# Pipecat Healthcare Booking Agent - Complete Project Documentation

## Project Overview

**Project Name**: pipecat-booking-agent  
**Type**: AI Voice Agent for Healthcare Appointment Booking  
**Framework**: Pipecat AI (Open-source Python conversational AI framework)  
**Primary Language**: Italian (testing support for English)  
**Python Version**: 3.11  
**Total Files**: 65 files, 30,969 lines of code  
**Container Registry**: rudyimhtpdev/voicebooking_piemo1:latest

### Purpose
Voice-based AI agent that handles natural conversation in Italian to book medical appointments at Cerba Healthcare facilities. The system manages complete booking workflows including service selection, center selection, slot booking, patient information collection, and SMS confirmations.

---

## Current Architecture & Critical Issues

### Deployment Flow (Current - SLOW)
```
Local Machine → Docker Build (4-6 hours) → DockerHub Push → Azure VM Pull → Deploy
```

### Critical Problem: 4-6 Hour Docker Build Time

**Root Cause**: Heavy ML/AI packages in requirements
- **torch**: ~800MB (PyTorch neural network framework)
- **torchaudio**: ~100MB (Audio processing for PyTorch)
- **pipecat-ai** with all extras (includes Silero VAD models)
- Combined with system dependencies (gcc, g++, ffmpeg)

**Impact on Business**:
- Extremely slow deployment cycles (4-6 hours per deployment)
- Cannot quickly push fixes or updates
- High development friction
- Extended downtime during deployments

### Scalability Problem: Single Container Architecture

**Current State**:
- ONE container handles ONE call at a time
- Manual scaling required for additional calls
- No auto-scaling infrastructure

**Business Requirements**:
- Target: 15-20 concurrent calls
- Daily volume: 500-600 calls
- Need: Each call gets its own container instance

**What's Needed**:
- Container orchestration (Kubernetes/ECS/similar)
- Auto-scaling policies
- Load balancing
- Session management across containers

---

## Technical Stack

### Core Framework: Pipecat AI

#### What is Pipecat?
Open-source Python framework for building real-time voice and multimodal conversational AI agents. Specialized for ultra-low latency voice interactions (500-800ms).

#### Pipecat Components in Use:
1. **pipecat-ai[daily,openai,silero,deepgram,elevenlabs,azure]** - Core framework with all service integrations
2. **pipecat-ai-flows** (v0.0.21) - Flow-based conversation management
3. **Pipeline System** - Audio/data processing pipeline
4. **Transport Layer** - WebSocket/WebRTC audio transmission
5. **Frame Processors** - Audio and transcript processing

### AI Services

#### Speech-to-Text (STT)
**Primary: Deepgram**
- Model: nova-3-general (53.4% better accuracy than Nova-2)
- Language: Italian (`it`)
- Sample Rate: 16000 Hz
- Features: Smart format, punctuation, interim results
- Keywords: "Maschio", "femmina", "cerba healthcare"

**Alternative: Azure STT** (configurable via `STT_PROVIDER` env var)
- Custom phrase list support for Italian medical terms
- Custom model endpoint support
- Language: it-IT
- Phrase list weight: 1.5x boost

**STT Switching**: Dynamic switching between default and email modes
- Email mode: Enhanced transcription for email dictation
- Implemented in `utils/stt_switcher.py`

#### Text-to-Speech (TTS)
**Provider**: ElevenLabs
- Model: eleven_multilingual_v2
- Voice ID: gfKKsLN1k0oYYN9n2dXX (Italian voice)
- Sample Rate: 16000 Hz
- Stability: 0.6
- Similarity Boost: 0.8
- Speaker Boost: Enabled

#### Language Model (LLM)
**Provider**: OpenAI
- Model: gpt-4.1-mini
- Temperature: 0.7 (for natural variation)
- Features: Function calling for service matching and state transitions
- Context: OpenAILLMContext aggregator manages conversation state

#### Voice Activity Detection (VAD)
**Provider**: Silero VAD
- **Critical Component**: This is why PyTorch is required
- Model: Downloaded at Docker build time via torch.hub.load()
- Storage: /opt/torch in container
- Configuration:
  - start_secs: 0.2
  - stop_secs: 0.5
  - min_volume: 0.4
- Optimized for Italian speech patterns

### Infrastructure

#### Azure Services
- **Azure VM**: Production deployment host
- **Azure MySQL**: Database (voila_tech_voice)
  - Call logging with 2-month retention
  - Stores: call_id, interaction_id, assistant_id, phone_number
  - Config: voikdbm74prodzj.mysql.database.azure.com
- **Azure Blob Storage**: 
  - Container: call-data
  - Stores: Call transcripts, recordings, fiscal codes, logs
  - 2-month auto-deletion for GDPR compliance
- **Redis Cache**: 
  - Host: VoilaVoice.redis.cache.windows.net
  - Port: 6380 (SSL)
  - Purpose: Session management, token caching, caller ID storage
  - TTL: 24 hours

#### External APIs
1. **Cerba Healthcare API**
   - Base URL: Production AWS endpoint
   - Authentication: OAuth2 with token refresh
   - Services:
     - `/amb/health-service` - Service search
     - `/amb/health-center` - Center search
     - `/amb/booking` - Booking creation
     - `/amb/slot` - Slot operations

2. **Twilio SMS**
   - Italian phone number normalization
   - Booking confirmation messages
   - Delivery status tracking

---

## File Structure Deep Dive

### Entry Points (3 Files)

#### 1. `bot.py` (495 lines) - PRODUCTION AGENT
**Purpose**: Main production server with FastAPI WebSocket transport

**Key Components**:
- **FastAPI App**: Healthcare Flow Bot v5.0.0
- **WebSocket Endpoint**: `/ws` with query parameters:
  - `business_status` - open/close (from Talkdesk)
  - `session_id` - Unique session identifier
  - `start_node` - Which flow node to start with
  - `caller_phone` - Caller ID from Talkdesk
  
- **RawPCMSerializer**: Custom serializer for 16kHz PCM audio
  - Handles InputAudioRawFrame (incoming)
  - Handles OutputAudioRawFrame (outgoing)
  
- **Pipeline Structure** (10 stages):
  1. FastAPI WebSocket Input (PCM from bridge)
  2. Deepgram STT (speech-to-text)
  3. UserIdleProcessor (50s timeout for transcription failures)
  4. TranscriptProcessor.user() (capture user speech)
  5. Context Aggregator User (add to conversation)
  6. OpenAI LLM (with flows + gender correction termina→femmina)
  7. ElevenLabs TTS (text-to-speech)
  8. FastAPI WebSocket Output (PCM to bridge)
  9. TranscriptProcessor.assistant() (capture assistant speech)
  10. Context Aggregator Assistant (add to conversation)

- **Session Management**:
  - Per-session transcript manager
  - Per-session call logger
  - Session timeout: 900 seconds (15 minutes)
  - Stores caller phone in Azure Storage
  
- **Event Handlers**:
  - `on_client_connected`: Initialize flow, start logging
  - `on_client_disconnected`: Extract call data, save to Azure
  - `on_session_timeout`: Save data even on timeout

- **Server Config**:
  - Host: 0.0.0.0 (configurable via HOST env var)
  - Port: 8080 (configurable via PORT env var)
  - CORS: Enabled for all origins

#### 2. `test.py` (636 lines) - VOICE TESTING
**Purpose**: Daily WebRTC testing with real voice interaction

**DailyTestConfig**:
- Max participants: 2 (bot + tester)
- Recording: local
- Session expires: 2 hours
- VAD params: Faster for testing (start: 0.1s, stop: 0.3s, volume: 0.2)

**DailyHealthcareFlowTester Class**:
- Creates Daily rooms via REST API
- Generates bot and user tokens
- Simulates caller phone from Talkdesk (--caller-phone flag)
- Simulates patient DOB (--patient-dob flag)
- **Pipeline**: Identical to bot.py but uses Daily transport instead of WebSocket

**Testing Features**:
- Start from any node: greeting, email, booking, name, phone, fiscal_code
- Pre-populate patient data for existing patient testing
- Full transcript recording
- Per-call logging with Azure upload

**Command Line Args**:
```bash
python test.py                                 # Full flow
python test.py --start-node booking            # Start from booking
python test.py --caller-phone +393333319326    # Simulate caller ID
python test.py --patient-dob 1979-06-19        # Simulate known patient
python test.py --debug                         # Debug mode
```

#### 3. `chat_test.py` (1,155 lines) - TEXT TESTING
**Purpose**: Text-only chat interface for rapid development (NO voice)

**Benefits**:
- 10x faster than voice testing
- No STT/TTS API costs
- Instant responses
- Browser-based UI with modern design
- Same flow logic as production

**Custom Processors**:
1. **TextInputProcessor**: Converts WebSocket text to TranscriptionFrame
2. **TextOutputProcessor**: Captures LLM output and streams to browser
3. **TextTransportSimulator**: Acts as transport layer for text-only

**Pipeline** (5 stages - NO STT/TTS):
1. TextTransportSimulator (WebSocket text input)
2. Context Aggregator User
3. OpenAI LLM (with flows)
4. TextOutputProcessor (captures and sends output)
5. Context Aggregator Assistant

**HTML UI Features**:
- Gradient animated background
- Message streaming with typing indicators
- Status bar with connection indicator
- Scrollable message container
- Auto-scroll to bottom
- Keyboard shortcuts (Enter to send)

**Access**: http://localhost:8081 (default port)

---

### Bridge Layer

#### `talkdeskbridge/bridge_conn.py` (922 lines) - TALKDESK INTEGRATION
**Purpose**: Bridges Talkdesk telephony system with Pipecat WebSocket server

**Architecture**:
- **FastAPI Server**: Runs on port 8080
- **WebSocket Endpoints**:
  - `/talkdesk` - Receives calls from Talkdesk
  - `/healthz` - Health check
  - `/escalation` - Handles call escalation/transfer

**Audio Processing**:
- **Format Conversion**: μ-law (Talkdesk) ↔ PCM (Pipecat)
- **Resampling**: 8kHz (Talkdesk) ↔ 16kHz (Pipecat)
- **Codec**: Linear16 PCM

**State Machine** (`BridgeState` enum):
1. `WAITING_START` - Waiting for START event from Talkdesk
2. `ACTIVE` - Bidirectional audio forwarding
3. `ESCALATING` - Transferring to human agent
4. `PIPECAT_CLOSED` - Pipecat session ended
5. `CLOSING` - Shutting down
6. `CLOSED` - Session ended

**Session Data Extraction**:
- `interaction_id` - Talkdesk interaction ID
- `caller_id` - Caller phone number
- `business_hours` - Open/close status (format: "...::open" or "...::close")
- `stream_sid` - Talkdesk stream identifier

**Audio Buffering**:
- Buffers audio packets while waiting for Pipecat to initialize
- Buffer limit: 100 packets
- Sends buffered audio once Pipecat is ready

**MySQL Logging**:
- Saves call completion to Azure MySQL
- Fields: call_id, assistant_id, interaction_id, phone_number, action
- Called on STOP event from Talkdesk

**Redis Storage**:
- Stores session mapping: call_id → interaction_id, stream_sid, caller_id
- TTL: 24 hours

**Escalation Flow**:
1. `/escalation` endpoint receives request
2. Closes Pipecat WebSocket
3. Waits for Pipecat completion (2s)
4. Fetches call statistics
5. Sends escalation message to Talkdesk with ringGroup format:
   - `{summary}::{sentiment}::{action}::{duration}::{service}`

---

### Configuration Layer

#### `config/settings.py` (135 lines) - CENTRALIZED CONFIGURATION

**Settings Class** - All configuration in one place:

```python
# API Keys
api_keys = {
    "deepgram": DEEPGRAM_API_KEY,
    "elevenlabs": ELEVENLABS_API_KEY,
    "openai": OPENAI_API_KEY,
    "azure_speech_key": AZURE_SPEECH_API_KEY,
    "azure_speech_region": AZURE_SPEECH_REGION
}

# STT Provider Selection
stt_provider = "deepgram"  # or "azure"

# Deepgram Configuration
deepgram_config = {
    "model": "nova-3-general",
    "language": "it",
    "sample_rate": 16000,
    "smart_format": True,
    "punctuate": True,
    "numerals": True,
    "keyterm": ["Maschio", "femmina", "cerba healthcare"]
}

# Azure STT Configuration
azure_stt_config = {
    "language": "it-IT",
    "sample_rate": 16000,
    "phrase_list": ["maschio", "femmina", "cerba healthcare"],
    "phrase_list_weight": 1.5
}

# ElevenLabs Configuration
elevenlabs_config = {
    "voice_id": "gfKKsLN1k0oYYN9n2dXX",
    "model": "eleven_multilingual_v2",
    "stability": 0.6,
    "similarity_boost": 0.8,
    "use_speaker_boost": True
}

# OpenAI Configuration
openai_config = {
    "model": "gpt-4.1-mini"
}

# VAD Configuration (Silero)
vad_config = {
    "start_secs": 0.2,
    "stop_secs": 0.5,
    "min_volume": 0.4
}

# Pipeline Configuration
pipeline_config = {
    "allow_interruptions": True,
    "enable_metrics": False,
    "enable_usage_metrics": False
}

# Language
language_config = "You need to speak Italian."
```

#### `services/config.py` (70 lines) - SERVICE CONFIGURATION

**Environment Variables**:
- `CERBA_TOKEN_URL` - OAuth token endpoint
- `CERBA_CLIENT_ID` - OAuth client ID
- `CERBA_CLIENT_SECRET` - OAuth client secret
- `CERBA_BASE_URL` - Cerba API base URL
- `SERVER_URL` - Server URL
- `CACHE_EXPIRY_HOURS` - Cache expiration (default: 1 hour)
- `REQUEST_TIMEOUT` - API timeout (default: 50 seconds)
- `DEFAULT_SEARCH_LIMIT` - Search result limit (default: 5)

**Validation**: Optional Cerba credentials - falls back to local data service if not provided

---

## Docker Configuration Analysis

### Current Dockerfile (67 lines) - Multi-Stage Build

```dockerfile
# Stage 1: base
FROM python:3.11-slim as base
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=8000
ENV NLTK_DATA=/usr/local/nltk_data
ENV TORCH_HOME=/opt/torch

# Stage 2: system-deps
FROM base as system-deps
RUN apt-get update && apt-get install -y \
    gcc g++ ffmpeg libsndfile1 portaudio19-dev python3-dev curl

# Stage 3: base-deps (SLOW - Heavy packages)
FROM system-deps as base-deps
COPY requirements-base.txt .
RUN pip install -r requirements-base.txt
# This installs: torch (~800MB), torchaudio (~100MB), pipecat-ai

# Stage 4: python-deps (Fast - Small packages)
FROM base-deps as python-deps
COPY requirements.txt .
RUN pip install -r requirements.txt
# This installs: azure-storage-blob

# Stage 5: nltk-data
FROM python-deps as nltk-data
RUN python -c "import nltk; nltk.download('punkt_tab', download_dir='/usr/local/nltk_data')"

# Stage 6: torch-models (SLOW - Downloads Silero VAD)
FROM nltk-data as torch-models
RUN mkdir -p /opt/torch && \
    python -c "import torch; torch.hub.set_dir('/opt/torch'); \
    torch.hub.load('snakers4/silero-vad', 'silero_vad', force_reload=True)"

# Stage 7: app (Frequent changes)
FROM torch-models as app
WORKDIR /app
RUN mkdir -p logs recordings data
COPY . .
RUN groupadd -r pipecat && useradd -r -g pipecat pipecat && \
    chown -R pipecat:pipecat /app /opt/torch
USER pipecat

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

EXPOSE $PORT

# Optimized uvicorn command
CMD ["python", "-m", "uvicorn", "bot:app", "--host", "0.0.0.0", "--port", "8000", 
     "--workers", "1", "--loop", "uvloop", "--backlog", "2048", "--limit-concurrency", "10"]
```

**Build Optimization Strategy**:
- Layer caching for stable dependencies
- Separate layers for frequent vs infrequent changes
- Pre-download models at build time (not runtime)
- Non-root user for security

**Why It's Still Slow**:
- Stage 3 (base-deps): Downloads ~1GB of packages
- Stage 6 (torch-models): Downloads Silero VAD models (~100MB)
- No layer reuse when base dependencies change
- Complete rebuild even for small code changes

### `docker-compose.yml` (38 lines)

```yaml
services:
  pipecat-agent:
    image: rudyimhtpdev/voicebooking_piemo1:latest
    container_name: healthcare-agent
    ports:
      - "8000:8000"
    environment:
      - PORT=8000
      - HOST=0.0.0.0
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
      - ./recordings:/app/recordings
```

**Current Limitations**:
- Single container only
- No scaling defined
- No environment file mounting
- No resource limits set
- No health checks defined

### `deploy.sh` (86 lines) - DEPLOYMENT SCRIPT

**Automated Deployment Process**:
1. Generates version tag: `v{TIMESTAMP}-{GIT_HASH}`
2. Builds Docker image locally
3. Tags as both versioned and `latest`
4. Pushes both tags to DockerHub
5. Generates Azure VM deployment commands
6. Saves deployment info to file

**Commands Generated**:
```bash
docker pull rudyimhtpdev/voicebooking_piemo1:latest
docker-compose down
docker-compose up -d
```

**Problem**: This entire process takes 4-6 hours due to Docker build time

---

## Dependencies Analysis

### `requirements-base.txt` (36 lines) - HEAVY STABLE PACKAGES

**AI/ML Packages** (Cause of slow builds):
```
pipecat-ai[daily,openai,silero,deepgram,elevenlabs,azure]
pipecat-ai-flows==0.0.21
torch==2.8.0              # ~800MB - Neural network framework
torchaudio==2.8.0         # ~100MB - Audio processing
```

**AI Service SDKs**:
```
deepgram-sdk==4.7.0       # STT
openai==1.99.1            # LLM  
anthropic==0.69.0         # Alternative LLM
google-genai==1.43.0      # Alternative LLM
```

**Web Framework**:
```
fastapi==0.119.0
uvicorn==0.37.0
websockets==15.0.1
uvloop==0.21.0            # High-performance event loop
```

**Core Libraries**:
```
requests==2.32.5
aiohttp==3.13.0
pydantic==2.12.0
numpy==2.2.6
python-dotenv==1.0.1
loguru==0.7.3
urllib3==2.5.0
python-json-logger==4.0.0
rapidfuzz==3.14.1         # Fuzzy matching
```

### `requirements.txt` (8 lines) - FAST REBUILD PACKAGES

```
azure-storage-blob>=12.19.0
```

**Strategy**: Separate frequently changing dependencies for faster Docker rebuilds

---

## Conversation Flow System (Pipecat Flows)

### Flow Manager (`flows/manager.py` - 165 lines)

**Core Function**: `create_flow_manager()`
- Initializes FlowManager with task, llm, context, transport
- Returns configured FlowManager instance

**Initialization Function**: `initialize_flow_manager(flow_manager, start_node)`

**Supported Start Nodes**:
1. **greeting** (default) - Full conversation from start
2. **email** - Email collection with STT switch
3. **phone** - Phone collection
4. **name** - Full name collection  
5. **fiscal_code** - Fiscal code generation
6. **slot_selection** - Pre-populated test booking
7. **booking** - Pre-populated service/center test

**Pre-population for Testing**:
- Service: RX Caviglia Destra (UUID: 9a93d65f-396a-45e4-9284-94481bdd2b51)
- Center: Rozzano Viale Toscana 35/37 - Delta Medica
- Patient: Male, DOB: 2007-04-27, Address: Milan

### Flow Architecture

#### Complete Flow Path:
```
1. Greeting
   ↓
2. Service Search (fuzzy matching)
   ↓
3. Service Selection (choose from top 3-5)
   ↓
4. Address Collection
   ↓
5. Gender Collection
   ↓
6. DOB Collection
   ↓
7. Basic Info Verification
   ↓
8. Flow Generation (decision tree based on service)
   ↓
9. Flow Navigation (LLM-driven questions)
   ↓
10. Finalize Services (add specialist visits if chosen)
   ↓
11. Center Search (for all services)
   ↓
12. Center Selection (top 3 centers)
   ↓
13. Cerba Membership Check
   ↓
14. DateTime Collection
   ↓
15. Slot Search
   ↓
16. Slot Selection (progressive filtering)
   ↓
17. Slot Booking (create_slot API call)
   ↓
18. Full Name Collection
   ↓
19. Phone Collection & Confirmation
   ↓
20. Email Collection & Confirmation (with STT switch)
   ↓
21. Reminder Authorization
   ↓
22. Marketing Authorization
   ↓
23. Final Booking Creation
   ↓
24. SMS Confirmation
   ↓
25. Success/Completion
```

### Flow Nodes (9 files in `flows/nodes/`)

#### 1. `greeting.py` (43 lines)
- Initial greeting
- Triggers service search
- Language setup

#### 2. `service_selection.py` (136 lines)
- Creates service selection node with found services
- Search retry node for failed searches
- Search processing node (intermediate TTS before actual search)

#### 3. `patient_info.py` (181 lines)
- Address collection
- Gender collection (m/f)
- DOB collection (YYYY-MM-DD)
- Basic info verification
- Flow processing node (intermediate TTS before flow generation)

#### 4. `patient_details.py` (271 lines)
- Full name collection (combined first + surname)
- Phone collection with confirmation
- Email collection with confirmation
- Reminder authorization (yes/no)
- Marketing authorization (yes/no)
- Booking processing node (intermediate TTS before booking)
- **Context Strategy**: RESET_WITH_SUMMARY after slot selection to clear heavy slot data

#### 5. `patient_summary.py` (118 lines)
- Patient data verification for existing patients
- Edit options (name, phone, fiscal code)
- Used when patient is found in database via phone+DOB

#### 6. `booking.py` (1,187 lines) - LARGEST NODE
**18 Node Creation Functions**:

1. `create_orange_box_node()` - Triggers flow generation
2. `create_flow_navigation_node()` - LLM-driven decision tree navigation
3. `create_final_center_search_node()` - Search centers with all services
4. `create_final_center_selection_node()` - Choose from top 3 centers
5. `create_no_centers_node()` - No centers found fallback
6. `create_cerba_membership_node()` - Cerba card check
7. `create_collect_datetime_node()` - Date/time collection with natural language
8. `create_collect_datetime_node_for_service()` - Service-specific date collection
9. `create_slot_search_node()` - Automatic slot search trigger
10. `create_slot_selection_node()` - **Most complex** (progressive filtering, 300+ lines)
11. `filter_slots_by_time_preference()` - Filter slots by morning/afternoon
12. `create_booking_creation_node()` - Booking confirmation (removed)
13. `create_slot_refresh_node()` - Refresh slots same day
14. `create_no_slots_node()` - No slots found fallback
15. `create_booking_summary_confirmation_node()` - Booking summary
16. `create_slot_booking_processing_node()` - Intermediate TTS before slot booking
17. `create_center_search_processing_node()` - Intermediate TTS before center search
18. `create_slot_search_processing_node()` - Intermediate TTS before slot search

**Special Features**:
- **First Available Mode**: When user says "most recent" or "earliest", searches from tomorrow
- **Progressive Slot Filtering**: Shows 4-6 slots initially, offers to show more
- **Smart Time Matching**: Handles various time formats, UTC↔Italian timezone conversion
- **Multi-service Support**: Books multiple services sequentially
- **Global Session Slots** (`_current_session_slots`): Maps display time → slot UUID for lookup

#### 7. `booking_completion.py` (121 lines)
- Final booking success message
- Displays booking details in Italian
- Offers to book another service or end call

#### 8. `completion.py` (149 lines)
- Error handling node
- Multi-booking success node
- Restart node
- All with Italian timezone display

#### 9. Node count: **18 node creator functions** total

### Flow Handlers (6 files in `flows/handlers/`)

#### 1. `service_handlers.py` (187 lines)
**4 Handler Functions**:
- `search_health_services_and_transition()` - Initiates service search with TTS
- `perform_health_services_search_and_transition()` - **Actual fuzzy search** (CPU intensive)
- `select_service_and_transition()` - Adds service to state, goes to address collection
- `refine_search_and_transition()` - Re-search with refined term

#### 2. `patient_handlers.py` (131 lines)
**4 Handler Functions**:
- `collect_address_and_transition()` - Stores address, validates, transitions
- `collect_gender_and_transition()` - Collects m/f with Italian terms (maschio/femmina)
- `collect_dob_and_transition()` - Validates date format (YYYY-MM-DD)
- `verify_basic_info_and_transition()` - Checks patient in DB via phone+DOB

#### 3. `patient_summary_handlers.py` (201 lines)
**4 Handler Functions**:
- `handle_patient_summary_response()` - Existing patient confirmation
- `handle_name_edit()` - Edit patient name
- `handle_phone_edit()` - Edit phone number
- `handle_fiscal_code_edit()` - Edit fiscal code (removed)

#### 4. `patient_detail_handlers.py` (621 lines) - LARGEST HANDLER
**11 Handler Functions**:
- `send_booking_confirmation_sms_async()` - Sends SMS after booking
- `start_email_collection_with_stt_switch()` - Entry point for email testing
- `collect_full_name_and_transition()` - Full name (no parsing)
- `collect_phone_and_transition()` - Phone with caller ID logic
- `confirm_phone_and_transition()` - Confirm/change phone
- `collect_email_and_transition()` - Email with validation
- `confirm_email_and_transition()` - Confirm/change email, skip to reminder auth
- `collect_reminder_authorization_and_transition()` - Yes/no for reminders
- `collect_marketing_authorization_and_transition()` - Yes/no for marketing
- `confirm_details_and_create_booking()` - Validates all data, initiates booking
- `perform_booking_creation_and_transition()` - **Actual booking API call**

**Critical Logic**:
- Fiscal code: Uses DB fiscal code if patient exists, else hardcoded "NWTSCI80A01F205A"
- Full name sent to BOTH name and surname API fields
- Extensive debug logging for all steps
- Validates booked_slots exist before creating booking
- Checks patient_found_in_db flag

#### 5. `flow_handlers.py` (241 lines)
**3 Handler Functions**:
- `generate_flow_and_transition()` - Initiates flow generation with TTS
- `perform_flow_generation_and_transition()` - **Calls genera_flow() API** (slow)
- `finalize_services_and_search_centers()` - Adds specialist services, searches centers

**Flow Generation Process**:
1. Gets health centers for primary service
2. Calls `genera_flow(hc_uuids, service_uuid)` from `services/get_flowNb.py`
3. Stores generated decision tree in state
4. Creates LLM-driven navigation node

#### 6. `booking_handlers.py` (1,306 lines) - LARGEST HANDLER
**12 Handler Functions**:

**Center Search** (2 functions):
- `search_final_centers_and_transition()` - Initiates center search
- `perform_center_search_and_transition()` - **Calls Cerba API** for centers

**Center Selection** (1 function):
- `select_center_and_book()` - Stores selected center, goes to Cerba membership

**Membership** (1 function):
- `check_cerba_membership_and_transition()` - Stores membership status for pricing

**DateTime Collection** (2 functions):
- `collect_datetime_and_transition()` - Parses natural language dates, handles first available
- `update_date_and_search_slots()` - Updates date and immediately searches slots

**Slot Search** (2 functions):
- `search_slots_and_transition()` - Initiates slot search
- `perform_slot_search_and_transition()` - **Calls list_slot() API** (returns slots)

**Slot Selection** (1 function):
- `select_slot_and_book()` - **Complex logic** (300+ lines):
  - Smart lookup via time→UUID mapping
  - Fallback to UUID matching
  - Timezone conversion (UTC→Italian)
  - Pricing extraction (Cerba vs non-Cerba)
  - Stores selected_slot in state
  - Creates slot booking processing node

**Slot Booking** (2 functions):
- `create_booking_and_transition()` - Confirms booking, initiates slot reservation
- `perform_slot_booking_and_transition()` - **Calls create_slot() API** to reserve slot
  - Converts datetime format for API
  - Stores in booked_slots array
  - Handles multi-service bookings sequentially

**Booking Modification** (1 function):
- `handle_booking_modification()` - Allows changes after completion

---

## Services Layer (16 files in `services/`)

### Core Services

#### 1. `auth.py` (106 lines) - AUTHENTICATION SERVICE
**AuthService Class**:
- OAuth2 token management
- Automatic token refresh
- 5-minute expiry buffer
- Token caching in memory

**Methods**:
- `get_token()` - Get valid token (auto-refreshes if expired)
- `_is_token_valid()` - Check expiry
- `_refresh_token()` - **POST** to Cerba token endpoint
- `clear_token()` - Force refresh

**Token Endpoint**:
- URL: Cognito OAuth2 endpoint
- Grant type: client_credentials
- Scope: voila/api

#### 2. `booking_api.py` (273 lines) - BOOKING CREATION
**Function**: `create_booking(booking_data)`

**API Call**:
- **POST** `/amb/booking`
- Headers: Authorization Bearer token
- Timeout: 50 seconds

**Request Format**:
```python
{
    "patient": {
        "name": "MARIO",
        "surname": "ROSSI",
        "email": "email@example.com",
        "phone": "+393333319326",
        "date_of_birth": "1980-01-01",
        "fiscal_code": "RSSMRA80A01F205X",
        "gender": "m"
    },
    "booking_type": "private",
    "health_services": [
        {
            "uuid": "service-uuid",
            "slot": "slot-uuid"  # From create_slot() response
        }
    ],
    "reminder_authorization": True,
    "marketing_authorization": False
}
```

**Response Handling**:
- 200/201: Success → Returns booking with code and UUID
- 400: Validation error
- 401: Auth error → clears token
- 409: Slot conflict (already booked)

**Function**: `validate_booking_data()` - Pre-validates data structure

#### 3. `cerba_api.py` (197 lines) - CERBA API SERVICE
**CerbaAPIService Class**:

**Methods**:
- `_make_request(endpoint, params)` - Authenticated GET requests
- `get_health_services(health_center)` - **GET** `/amb/health-service`
- `get_health_centers(...)` - **GET** `/amb/health-center`

**Parameters for get_health_centers()**:
- `health_services`: Comma-separated UUIDs
- `gender`: "m" or "f"
- `date_of_birth`: YYYYMMDD format
- `address`: Location to search
- `health_services_availability`: True/False

**Error Handling**:
- 401: Clears cached token
- 4xx/5xx: Raises CerbaAPIError

#### 4. `slotAgenda.py` (138 lines) - SLOT MANAGEMENT

**Function**: `list_slot()` - Search available slots
**API**: **GET** `/amb/health-center/{uuid}/slot`
**Parameters**:
- `health_center_uuid`: Center UUID
- `date_search`: YYYY-MM-DD
- `uuid_exam`: Service UUID list
- `gender`: m/f
- `date_of_birth`: YYYYMMDD
- `start_time`: Optional (YYYY-MM-DD HH:MM:SS+00)
- `end_time`: Optional (YYYY-MM-DD HH:MM:SS+00)
- `availabilities_limit`: 3

**Returns**: List of slot objects with:
- `start_time`: UTC datetime
- `end_time`: UTC datetime
- `providing_entity_availability_uuid`: For slot selection
- `health_services[]`: Array with price info
- `health_center`: Center details

**Function**: `create_slot()` - Reserve a slot
**API**: **POST** `/amb/slot`
**Body**:
```python
{
    "start_time": "2025-10-27 11:25:00",
    "end_time": "2025-10-27 11:30:00",
    "providing_entity_availability": "pea-uuid"
}
```
**Returns**: `uuid` (slot reservation UUID), `created_at`

**Function**: `delete_slot()` - Cancel slot
**API**: **DELETE** `/amb/slot/{uuid}`

#### 5. `fuzzy_search.py` (245 lines) - SERVICE MATCHING
**FuzzySearchService Class**:

**Methods**:
- `_get_services()` - Loads services from local_data_service (cached)
- `_expand_search_terms()` - Expands Italian search terms
- `_create_service_search_text()` - Joins name, code, synonyms
- `_calculate_service_score()` - **Complex scoring algorithm**
- `search_services()` - Main search function

**Scoring Algorithm** (0-100 points):
1. **Exact Keyword Matching** (up to 80 points):
   - Medical keywords: +25 points each (radiografia, rx, caviglia, etc.)
   - Regular keywords: +15 points each
   
2. **Fuzzy Matching** (30% weight):
   - Partial ratio on name and full text
   
3. **Token-based Matching** (20% weight):
   - Handles word order differences
   
4. **Individual Word Matching** (up to 30 points):
   - +15 points per matching word
   
5. **Irrelevant Penalty** (-20 points):
   - Filters: "peeling", "gemellare", "fetale", "pediatrica"

**Threshold**: Minimum score 40 to be included
**Cache**: 1 hour expiry
**Data Source**: `data/all_services.json` (425KB, ~8,000 services)

#### 6. `fiscal_code_generator.py` (264 lines) - FISCAL CODE GENERATION
**FiscalCodeGenerator Class**:

**Purpose**: Generate Italian "Codice Fiscale" from patient data

**Dependencies**:
- `extractCF.py` (8,347 lines) - Core fiscal code algorithm
- `city_codes.json` (206KB) - 8,000+ Italian city cadastral codes

**Methods**:
- `normalize_city_name()` - Cleans city names (removes accents, prefixes)
- `find_city_code()` - Fuzzy matches city to cadastral code
- `generate_fiscal_code()` - **Main generation function**
- `validate_fiscal_code()` - Format validation

**Generation Process**:
1. Validates required fields: name, surname, birth_date, gender, birth_city
2. Normalizes gender to m/f
3. Fuzzy matches birth city to find cadastral code (80% threshold)
4. Calls `calculate_tax_code()` from extractCF.py
5. Returns fiscal code with generation metadata

**Format**: 16 characters (e.g., RSSMRA80A01F205X)
- 6 letters (surname + name encoding)
- 2 digits + 1 letter + 2 digits (date of birth + gender)
- 1 letter + 3 chars + 1 letter (city code + check digit)

#### 7. `transcript_manager.py` (383 lines) - CONVERSATION RECORDING
**TranscriptManager Class**:

**Purpose**: Records, summarizes, and stores conversation data

**Data Structures**:
- `TranscriptMessage`: role, content, timestamp
- `conversation_log`: List of all messages
- `session_start_time`: Session start datetime

**Methods**:
- `start_session()` - Initialize new session
- `add_user_message()` / `add_assistant_message()` - Record messages
- `get_conversation_duration()` - Calculate duration in seconds
- `generate_conversation_summary()` - Basic rule-based summary
- `generate_ai_summary()` - **OpenAI-powered summary** (gpt-4-mini)
- `_append_personal_details_to_summary()` - Adds GDPR-sensitive data
- `extract_and_store_call_data()` - **Main extraction function**
- `get_transcript_json()` - Export as JSON

**AI Summary Prompt**:
```
Analyze conversation and summarize:
1. What services did patient want?
2. Was booking completed? (date, time, location, services)
3. Conversation flow and outcome
4. Issues, cancellations, rescheduling?
5. Authorization given (reminders, marketing)?
6. Overall success and satisfaction
```

**Stored Data Structure**:
```python
{
    "session_id": "session-xxx",
    "timestamp": "ISO-8601",
    "call_duration_seconds": 180,
    "fiscal_code": "RSSMRA80A01F205X",
    "patient_data": {...},
    "booking_data": {...},
    "transcript": [...],
    "summary": "AI-generated summary",
    "reminder_authorization": True,
    "marketing_authorization": False
}
```

**Storage**: Azure Blob Storage via `CallDataStorage`

**Session Management**:
- `_transcript_managers` dict - Session-specific managers
- `get_transcript_manager(session_id)` - Get or create manager
- `cleanup_transcript_manager(session_id)` - Clean up after session

#### 8. `call_logger.py` (286 lines) - PER-CALL LOGGING
**CallLogger Class**:

**Purpose**: Session-specific log files for debugging

**File Naming**: `{YYYYMMDD_HHMMSS}_{session_id[:8]}_{phone}.log`

**Features**:
- Loguru handler for structured logging
- Session-specific Python logger
- Filters out noisy logs (BINARY, websocket keep-alive)
- Azure Blob Storage upload (background thread)
- Automatic cleanup (7-day retention)

**Custom Handler**: `CallFileHandler`
- Skips binary logs
- Formats: timestamp | level | name | session_id - message
- UTF-8 encoding for Italian characters

**Helper Methods**:
- `log_phone_debug()` - Phone number debugging
- `log_flow_transition()` - Node transitions
- `log_user_input()` - User speech with confidence
- `log_agent_response()` - Agent replies with timing
- `log_api_call()` - API calls with duration
- `log_error()` - Errors with context

**Azure Upload Path**: `call-logs/{YYYY-MM-DD}/{filename}.log`

#### 9. `call_storage.py` (342 lines) - AZURE BLOB STORAGE
**CallDataStorage Class**:

**Container**: call-data

**Methods**:
- `store_call_data()` - Store complete call data
- `retrieve_call_data()` - Retrieve by session_id
- `list_recent_calls()` - List with metadata
- `store_fiscal_code_only()` - Separate fiscal code storage
- `store_caller_phone()` - Store Talkdesk caller ID
- `retrieve_caller_phone()` - Retrieve caller ID
- `_upload_text_content()` - Generic text upload

**Blob Paths**:
- `calls/{YYYY-MM-DD}/{timestamp}_{session_id}.json`
- `fiscal-codes/{YYYY-MM-DD}/{timestamp}_{session_id}_fiscal.json`
- `caller-phones/{YYYY-MM-DD}/{timestamp}_{session_id}_phone.json`
- `call-logs/{YYYY-MM-DD}/{logfile}.log`

**Metadata Stored**:
- session_id
- timestamp
- date
- has_fiscal_code (boolean)
- patient_name
- has_booking (boolean)
- transcript_messages (count)
- call_duration_seconds

#### 10. `sms_service.py` (304 lines) - TWILIO SMS
**TwilioSMSService Class**:

**Configuration**:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`

**Methods**:
- `_normalize_italian_phone()` - Adds +39 country code
- `_create_booking_confirmation_message()` - Italian SMS template
- `send_booking_confirmation()` - Async sending
- `send_booking_confirmation_sync()` - Sync sending
- `get_delivery_status()` - Check delivery status

**SMS Template** (Italian):
```
🏥 Cerba Healthcare - Conferma Prenotazione

Gentile {patient_name},
La sua prenotazione è confermata:

📋 Servizio: {service_name}
📍 Centro: {center_name}
📅 Data: {booking_date}
🕐 Ora: {booking_time}

Codice: {booking_id}

Per modifiche: +39 02 xxxxx
Per annullare rispondi STOP

Cerba Healthcare
```

#### 11. `timezone_utils.py` (131 lines) - ITALIAN TIMEZONE HANDLING
**Functions**:
- `utc_to_italian_display()` - UTC → "Europe/Rome" display format
- `italian_to_utc_for_api()` - Italian → UTC for API calls
- `convert_slot_times_to_italian()` - Bulk conversion
- `format_time_for_display()` - User-friendly formatting

**Critical**: All slot times from API are UTC, converted to Italian for display

#### 12. `local_data_service.py` (176 lines) - LOCAL SERVICE DATA
**LocalDataService Class**:

**Purpose**: Loads services from local JSON instead of Cerba API

**Data File**: `data/all_services.json` (425KB)
- ~8,000 healthcare services
- Format: {"services": [{uuid, name, code, synonyms}, ...]}

**Path Resolution** (Docker-compatible):
1. Environment variable: `DATA_FILE_PATH`
2. Current working directory: `./data/all_services.json`
3. Project root: relative path
4. Container path: `/app/data/all_services.json`

**Methods**:
- `get_health_services()` - Returns all services (cached)
- `get_service_count()` - Total count
- `search_services_by_name()` - Simple name/synonym search

#### 13. `patient_lookup.py` (202 lines) - PATIENT DATABASE
**In-Memory Patient Store** (for testing):
```python
PATIENTS_DB = [
    {
        "id": "p1",
        "phone": "+393333319326",
        "first_name": "Rudy",
        "last_name": "Crapella",
        "dob": "1979-06-19",
        "fiscal_code": "FC10001",
        "email": "rudy.crapella@gmail.com"
    },
    # ... more patients
]
```

**Functions**:
- `normalize_phone()` - Formats to +39XXXXXXXXXX
- `normalize_dob()` - Validates YYYY-MM-DD
- `lookup_by_phone_and_dob()` - Finds patient record
- `populate_patient_state()` - Fills flow_manager state
- `get_patient_summary_text()` - Confirmation message for existing patients

**Lookup Logic**:
- Matches normalized phone + DOB
- If found: Skips name/phone/email/fiscal code collection
- If not found: Collects all details as new patient

#### 14. `get_flowNb.py` (356 lines) - FLOW GENERATION API
**Function**: `genera_flow(hc_uuids, service_uuid)`

**Purpose**: Calls external API to generate decision tree for service

**Process**:
1. Calls `recupera_amb_json_flow()` from `amb_json_flow_eng.py`
2. Receives decision tree JSON structure
3. Returns flow with questions, branches, list_health_services

**Function**: `aggiungi_unico()` - Deduplicates flow nodes

#### 15. `idle_handler.py` (142 lines) - TIMEOUT HANDLING
**Functions**:
- `healthcare_idle_callback()` - Healthcare-specific timeout prompt
- `create_user_idle_processor()` - Creates UserIdleProcessor
- `simple_idle_callback()` - Generic timeout prompt
- `create_simple_idle_processor()` - Simple processor

**Timeout**: 50 seconds (accounts for API processing delays)

**Prompt on Timeout**:
"Are you still there? If you need more time, just let me know. I'm here to help you book your appointment."

#### 16. `amb_json_flow_eng.py` (199 lines) - FLOW ENGINE
**Function**: `recupera_amb_json_flow()`
- Placeholder/stub for flow generation
- Returns decision tree structure

---

## Pipeline Components

### `pipeline/components.py` (214 lines)

**AzureSTTServiceWithPhrases Class**:
- Extends AzureSTTService
- Adds phrase list support
- Uses SpeechSDK PhraseListGrammar
- Applies phrase_list_weight boost

**Service Creation Functions**:

1. **`create_stt_service()`** - Router function
   - Checks `settings.stt_provider`
   - Returns Deepgram or Azure STT

2. **`create_deepgram_stt_service()`**:
   - Creates DeepgramSTTService
   - Configures LiveOptions with all settings
   - Debug logging for API key and config

3. **`create_azure_stt_service()`**:
   - Creates AzureSTTServiceWithPhrases
   - Maps language codes to Language enum
   - Sets up phrase list if configured

4. **`create_tts_service()`**:
   - Creates ElevenLabsTTSService
   - All ElevenLabs config from settings

5. **`create_llm_service()`**:
   - Creates OpenAILLMService
   - Model: gpt-4.1-mini

6. **`create_context_aggregator()`**:
   - Creates OpenAILLMContext
   - Manages conversation history

### `pipeline/setup.py` (83 lines)

**Functions**:
- `create_transport()` - Daily transport setup
- `create_pipeline_task()` - Complete pipeline with recording

**Note**: Not used in current bot.py/test.py (they build pipelines directly)

### `pipeline/recording.py` (396 lines) - AUDIO RECORDING
**SessionRecorder Class**:

**Purpose**: Records audio in 30-second chunks

**Audio Quality**:
- Sample Rate: 16000 Hz (VAD-compatible)
- Channels: 2 (stereo - user left, bot right)
- Format: WAV
- Chunk Duration: 30 seconds

**Directory Structure**:
```
recordings/
├── audios/
│   └── {session_id}/
│       ├── chunks/           # 30-second chunks
│       │   ├── chunk_001_complete_{time}.wav
│       │   ├── chunk_001_patient_{time}.wav
│       │   └── chunk_001_assistant_{time}.wav
│       └── final_audio/      # Combined files
│           ├── {session_id}_complete_conversation.wav
│           ├── {session_id}_patient_audio.wav
│           └── {session_id}_assistant_audio.wav
└── transcripts/
    └── {session_id}_transcript.json
```

**Combination Methods**:
- Prefers FFmpeg if available
- Falls back to Python wave module
- Combines chunks in chronological order

**Event Handlers**:
- `on_audio_data` - Saves 30s stereo chunks
- `on_track_audio_data` - Saves separate user/bot tracks
- `on_user_turn_audio_data` - Saves individual speaking turns

---

## Utilities

### `utils/logging.py` (210 lines)
**ColoredFormatter Class**: ANSI color codes for terminal
**RequestLogger Class**: HTTP request logging

**Functions**:
- `setup_logging()` - Configure loguru
- `get_logger()` - Get named logger
- `log_function_call()` - Decorator for function logging
- `log_api_call()` - API call logging
- `setup_environment_logging()` - Environment-based logging levels

### `utils/cache.py` (238 lines)
**TTLCache Class**: Time-based cache with automatic expiry

**Features**:
- Thread-safe with Lock
- Automatic expiry cleanup
- Statistics tracking
- Cache decorator

**CachedFunction Class**: Decorator for caching function results

### `utils/stt_switcher.py` (102 lines)
**STTSwitcher Class**:

**Purpose**: Switch between default and email transcription modes

**Modes**:
- **Default**: General conversation (Nova-3 general)
- **Email**: Enhanced for email dictation (Nova-3 email mode)

**Implementation**:
- Uses DeepgramSTTService
- Sends STTUpdateSettingsFrame
- Updates LiveOptions in real-time

**Functions**:
- `switch_to_email_mode()` - Email transcription
- `switch_to_default_mode()` - General transcription  
- `initialize_stt_switcher()` - Setup switcher with flow_manager

**Note**: Currently DISABLED in code - using Nova-3 general for all

---

## Data Models

### `models/requests.py` (49 lines)

```python
class HealthService(BaseModel):
    uuid: str
    name: str
    code: str
    synonyms: List[str]

class HealthCenter(BaseModel):
    uuid: str
    name: str
    address: str
    city: str
    district: str
    phone: str
    region: str

class HealthCenterRequest(BaseModel):
    service_ids: List[str]
    location: str

class ServiceSearchRequest(BaseModel):
    query: str
    filters: Optional[Dict]
```

### `models/responses.py` (67 lines)

```python
class HealthServiceResponse(BaseModel):
    services: List[HealthService]
    total: int

class HealthCenterResponse(BaseModel):
    centers: List[HealthCenter]
    total: int

class ServiceSearchResponse(BaseModel):
    found: bool
    count: int
    services: List[HealthService]
    search_term: str
    message: Optional[str]

class ToolCallResult(BaseModel):
    success: bool
    data: Any
    error: Optional[str]

class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime

class ErrorResponse(BaseModel):
    error: str
    details: Optional[str]
```

---

## Environment Variables Required

### Core AI Services (Required)
```bash
DEEPGRAM_API_KEY=your_deepgram_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
OPENAI_API_KEY=your_openai_api_key
```

### Azure STT (Optional - if using Azure instead of Deepgram)
```bash
AZURE_SPEECH_API_KEY=your_azure_speech_key
AZURE_SPEECH_REGION=your_azure_region
AZURE_SPEECH_ENDPOINT_ID=optional_custom_model
STT_PROVIDER=azure  # Set to 'azure' to use Azure STT
DISABLE_PHRASE_LIST=false  # Set to 'true' to disable phrase list
```

### Daily Testing (Development Only)
```bash
DAILY_API_KEY=your_daily_api_key
DAILY_API_URL=https://api.daily.co/v1
```

### Production Server
```bash
HOST=0.0.0.0
PORT=8000
PIPECAT_SERVER_URL=ws://azure_vm_ip:8000/ws
```

### Azure Storage
```bash
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
```

### Twilio SMS
```bash
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_twilio_number
```

### Cerba Healthcare API (Optional - uses local data if not provided)
```bash
CERBA_TOKEN_URL=https://cerbahc.auth.eu-central-1.amazoncognito.com/oauth2/token
CERBA_CLIENT_ID=your_client_id
CERBA_CLIENT_SECRET=your_client_secret
CERBA_BASE_URL=https://3z0xh9v1f4.execute-api.eu-south-1.amazonaws.com/prod
```

### Cache & Performance
```bash
CACHE_EXPIRY_HOURS=1
REQUEST_TIMEOUT=50
DEFAULT_SEARCH_LIMIT=5
```

---

## Deployment Deep Dive

### Current Docker Build Process

**Multi-Stage Build Breakdown**:

1. **base** - Python 3.11-slim + env vars (< 1 second)
2. **system-deps** - Install gcc, g++, ffmpeg, etc. (~2-3 minutes)
3. **base-deps** - Install requirements-base.txt (***2-4 HOURS***)
   - Downloading torch (~800MB)
   - Downloading torchaudio (~100MB)
   - Compiling native extensions
   - Installing all pipecat extras
4. **python-deps** - Install requirements.txt (~30 seconds)
   - Only azure-storage-blob
5. **nltk-data** - Download punkt_tab (~10 seconds)
6. **torch-models** - Download Silero VAD (***10-30 minutes***)
   - torch.hub.load('snakers4/silero-vad')
   - Stored in /opt/torch
7. **app** - Copy code + create user (~10 seconds)

**Total Build Time**: 4-6 hours (mostly stages 3 & 6)

### Current Deployment Workflow

**Step 1: Local Development**
```bash
# Test with text (fast - recommended 90% of time)
python chat_test.py
python chat_test.py --start-node booking

# Test with voice (slower - final 10% validation)
python test.py
python test.py --start-node email
```

**Step 2: Docker Build & Push** (`deploy.sh`)
```bash
#!/bin/bash
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
GIT_HASH=$(git rev-parse --short HEAD)
VERSION_TAG="v${TIMESTAMP}-${GIT_HASH}"

# Build with version and latest tags (4-6 HOURS!)
docker build -t rudyimhtpdev/voicebooking_piemo1:${VERSION_TAG} .
docker tag rudyimhtpdev/voicebooking_piemo1:${VERSION_TAG} rudyimhtpdev/voicebooking_piemo1:latest

# Push to DockerHub
docker push rudyimhtpdev/voicebooking_piemo1:${VERSION_TAG}
docker push rudyimhtpdev/voicebooking_piemo1:latest
```

**Step 3: Azure VM Deployment**
```bash
# On Azure VM
docker pull rudyimhtpdev/voicebooking_piemo1:latest
docker-compose down
docker-compose up -d
docker image prune -f
```

**Step 4: Verify**
```bash
docker logs healthcare-agent
curl http://localhost:8000/health
```

### Container Runtime Configuration

**From Dockerfile CMD**:
```bash
uvicorn bot:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1 \              # Single worker (1 process)
  --loop uvloop \             # High-performance event loop
  --backlog 2048 \            # Connection queue size
  --limit-concurrency 10      # Max 10 concurrent connections
```

**Problems with Current Setup**:
- Single worker = single call capacity
- Limited concurrency (10 connections max)
- No horizontal scaling
- Manual container management

---

## Call Flow Technical Details

### Session Lifecycle

#### 1. Incoming Call (Talkdesk)
- Talkdesk sends WebSocket to bridge_conn.py
- Bridge receives START event with:
  - `stream_sid`
  - `interaction_id`
  - `caller_id` (phone number)
  - `business_hours` (open/close status)

#### 2. Bridge Processing
- Extracts business_status from business_hours
- Buffers incoming audio (up to 100 packets)
- Creates Pipecat WebSocket connection with parameters:
  - `business_status=open` or `close`
  - `session_id={uuid}`
  - `caller_phone={caller_id}`
- Stores in Redis: call_id → {interaction_id, stream_sid, caller_id}

#### 3. Pipecat Bot Initialization (bot.py)
- Accepts WebSocket connection
- Extracts query parameters
- Validates API keys (Deepgram, ElevenLabs, OpenAI)
- Creates pipeline with 10 stages
- Starts CallLogger (per-session log file)
- Creates FlowManager
- Stores caller_phone in flow state AND Azure Storage
- Initializes STT switcher
- Sets up event handlers
- Runs PipelineRunner

#### 4. Conversation Processing
- Audio: Talkdesk (μ-law 8kHz) → Bridge (convert) → Pipecat (PCM 16kHz)
- STT: Deepgram converts speech to text
- Idle Detection: 50s timeout if no speech
- Transcript: User messages captured
- LLM: OpenAI processes with flow logic
- TTS: ElevenLabs generates voice
- Audio Out: Pipecat (PCM 16kHz) → Bridge (convert) → Talkdesk (μ-law 8kHz)
- Transcript: Assistant messages captured

#### 5. Flow Transitions
- FlowManager handles state transitions
- Each handler returns (result, next_node)
- Nodes can have pre_actions for immediate TTS
- State persisted across entire conversation

#### 6. Booking Creation
- Collects: Services, center, slots, patient details
- Calls create_slot() to reserve each slot
- Calls create_booking() with all data
- Sends SMS confirmation via Twilio
- Stores booking code in state

#### 7. Session Termination
**On Disconnect** (`on_client_disconnected`):
- Calls `extract_and_store_call_data()`
- Generates AI summary via OpenAI
- Stores complete data in Azure Blob Storage
- Uploads call log to Azure
- Cleans up transcript manager
- Cancels pipeline task

**On Timeout** (`on_session_timeout`):
- Same as disconnect
- Ensures data saved even on timeout

**On Talkdesk STOP**:
- Saves to MySQL with caller_id
- Removes from Redis
- Closes Pipecat connection

#### 8. Data Persistence
- **Azure Blob**: Call data, transcripts, logs, fiscal codes
- **Azure MySQL**: Call statistics for reporting
- **Local Files**: Temporary log files (uploaded then kept)

---

## Key Technical Patterns

### 1. Intermediate Processing Nodes
**Pattern**: TTS message → API call → Result

**Example**: Center Search
```
search_final_centers_and_transition()
  → create_center_search_processing_node(status_text)
      → pre_actions: [tts_say: "Sto cercando..."]
      → function: perform_center_search_and_transition()
          → Actual cerba_api.get_health_centers() call
          → create_final_center_selection_node(results)
```

**Purpose**: User hears status while API call executes in background

**Used for**:
- Service search (fuzzy matching)
- Center search (Cerba API)
- Slot search (Cerba API)
- Flow generation (genera_flow API)
- Booking creation (booking API)
- Slot booking (create_slot API)

### 2. Progressive Slot Filtering
**Algorithm** (`create_slot_selection_node` in booking.py):

**Input**: Full list of slots from API
**Output**: 4-6 slots shown to user, with "show more" option

**Steps**:
1. Parse all slots (convert UTC→Italian time)
2. Group by date
3. **First Available Mode**:
   - Show ALL slots from tomorrow
   - Highlight earliest time
   - Mention morning/afternoon distribution
4. **Regular Mode**:
   - Filter by user's preferred date
   - Apply time preference (morning 8-12, afternoon 12-19, specific time)
   - Show first 4-6 slots
   - Cache remaining slots for "show more"
5. Create slot-time mapping in `_current_session_slots` global
6. Build LLM instructions with slot details

**Smart Features**:
- Avoids sending 100+ slots to LLM (context bloat)
- Allows progressive disclosure
- Maintains fast response times
- Preserves all slots for "show more" requests

### 3. Context Management Strategy
**Default**: Conversation context accumulates (all messages kept)

**RESET_WITH_SUMMARY** (used in patient_details.py):
- Triggered at `create_collect_full_name_node()`
- Clears heavy slot data from context
- Keeps only summary: patient name, service, appointment date/time
- Prevents context window bloat
- Improves LLM performance

**Prompt for Summary**:
"Summarize ONLY: patient name, selected healthcare service, booked appointment date and time. DO NOT include slot details, UUIDs, or availability data."

### 4. Session-Specific Resource Management

**Pattern**: One instance per session (avoids cross-session contamination)

**Implemented in**:
- `get_transcript_manager(session_id)` - Dictionary of managers
- `CallLogger(session_id)` - Instance per session
- `active_sessions[session_id]` - FastAPI session tracking

**Cleanup**:
- `cleanup_transcript_manager(session_id)` - Deletes from dictionary
- `session_call_logger.stop_call_logging()` - Closes handlers
- `del active_sessions[session_id]` - Removes tracking

---

## Testing Framework Details

### Voice Testing Capabilities (`test.py`)

**Daily Room Creation**:
- Creates public room (easier testing)
- Max participants: 10
- Enable chat: True
- Expiry: 2 hours
- Generates bot token + user token

**Event Handlers** (matches bot.py):
- `on_participant_joined` - Start transcript, initialize flow
- `on_participant_left` - Extract data, cleanup
- `on_audio_track_started/stopped` - Audio debugging
- `on_call_state_updated` - State transitions
- `on_error` - Error handling

**Pre-population Testing**:
- `--caller-phone +393333319326` - Simulates known patient Rudy
- `--patient-dob 1979-06-19` - Matches DB record
- Skips phone confirmation step
- Uses DB fiscal code

### Text Testing Capabilities (`chat_test.py`)

**WebSocket Protocol**:
```javascript
// Client → Server
{
    "type": "user_message",
    "text": "I need an ECG"
}

// Server → Client (streaming)
{
    "type": "assistant_message_chunk",
    "text": "partial text"
}

// Server → Client (complete)
{
    "type": "assistant_message_complete",
    "text": "complete message"
}

// Server → Client (ready)
{
    "type": "system_ready",
    "start_node": "greeting"
}
```

**Message Queue**: Ensures messages wait for pipeline StartFrame

**Advantages**:
- No audio encoding/decoding
- No network jitter
- Exact text visibility
- Faster debugging
- Lower API costs (no STT/TTS)

---

## Performance Characteristics

### API Call Latency

**Slowest Operations**:
1. **Flow Generation** (`genera_flow`) - 5-15 seconds
   - External API call
   - Decision tree computation
   
2. **Center Search** (`get_health_centers`) - 2-5 seconds
   - Multiple services filtering
   - Geographic search
   
3. **Slot Search** (`list_slot`) - 1-3 seconds per service
   - Availability calculation
   - Multiple date/time ranges
   
4. **Fuzzy Search** (`search_services`) - 0.5-2 seconds
   - Scores ~8,000 services
   - Fuzzy matching algorithms
   
5. **Booking Creation** (`create_booking`) - 1-2 seconds
   - Transaction processing
   - Validation

**Fast Operations**:
- Authentication (`get_token`) - <100ms (cached)
- Slot Booking (`create_slot`) - 200-500ms
- Patient Lookup - <50ms (in-memory)

### Resource Usage

**Memory** (per container):
- PyTorch models: ~500MB baseline
- Pipecat framework: ~200MB
- Application code: ~50MB
- Per session: ~10-20MB (audio buffers, transcript)
- **Total**: ~800MB-1GB per container

**CPU**:
- Silero VAD: Light (runs on CPU)
- Audio processing: Light (PCM conversion, resampling)
- LLM: Offloaded to OpenAI
- STT/TTS: Offloaded to services

**Disk**:
- Docker image: ~3-4GB (due to torch + torchaudio)
- Logs: ~1-5MB per call
- Recordings: ~5-20MB per call (30-second chunks)

### Concurrency Limits

**Current Settings** (from Dockerfile):
- Workers: 1 (single uvicorn process)
- Limit concurrency: 10 (max connections)
- Backlog: 2048 (queue size)

**Actual Capacity**: 
- 1 call per container (due to stateful session management)
- Would need 20 containers for 20 concurrent calls

---

## Code Statistics

### Complexity Analysis

**Largest Files** (by lines):
1. `extractCF.py` - 8,347 lines (fiscal code algorithm + city data)
2. `flows/handlers/booking_handlers.py` - 1,306 lines
3. `flows/nodes/booking.py` - 1,187 lines
4. `chat_test.py` - 1,155 lines (includes HTML UI)
5. `talkdeskbridge/bridge_conn.py` - 922 lines

**Function Distribution**:
- **Total Functions**: 289
- **Most functions**: `flows/handlers/booking_handlers.py` (12 functions)
- **Complex handlers**: Patient details, booking, flow navigation

**Class Distribution**:
- **Total Classes**: 50
- **Service Classes**: 15 (Auth, Storage, Logger, etc.)
- **Data Models**: 13 (Requests, Responses)
- **Processors**: 7 (Input, Output, Transport)
- **Configuration**: 4 (Settings, Config, TestConfig)

**Import Dependencies**:
- **Total Imports**: 685
- **No Circular Dependencies** (verified by ContextEngineMCP)
- **Most Imported**: `config/settings.py` (17 dependents)

---

## Business Logic Implementation

### Service Matching Algorithm

**Location**: `services/fuzzy_search.py`

**Input**: User query (e.g., "radiografia caviglia")

**Process**:
1. Load 8,000 services from `data/all_services.json`
2. Expand search terms (split words, normalize)
3. For each service:
   - Create searchable text (name + code + synonyms)
   - Calculate score (0-100):
     - Exact keyword match: +25 (medical) or +15 (regular)
     - Fuzzy match: 30% weight
     - Token match: 20% weight
     - Word match: +15 per word
     - Irrelevant penalty: -20
4. Filter score >= 40
5. Sort by score (highest first)
6. Return top N results (default 5)

**Performance**: 
- Cached for 1 hour
- Searches ~8,000 services in 0.5-2 seconds

### Booking Creation Workflow

**Location**: Multiple handlers coordinate

**Data Collection Order**:
1. **Service Selection**: UUID, name from fuzzy search
2. **Patient Basic Info**: Address, gender, DOB
3. **Flow Navigation**: Optional additional services
4. **Center Selection**: UUID, name, city from Cerba API
5. **Membership**: is_cerba_member (affects pricing)
6. **DateTime**: preferred_date, time_preference
7. **Slot Selection**: providing_entity_availability_uuid, times
8. **Slot Reservation**: Calls create_slot() → returns slot_uuid
9. **Patient Details**: Full name, phone, email
10. **Authorizations**: Reminder, marketing (true/false)
11. **Final Booking**: Calls create_booking() with all data

**Critical**: `booked_slots` array must exist before final booking
- Each element: {slot_uuid, service_name, start_time, end_time, price}
- Created by `perform_slot_booking_and_transition()`
- Validated in `confirm_details_and_create_booking()`

### Fiscal Code Generation

**Location**: `services/fiscal_code_generator.py` + `extractCF.py`

**Current Status**: Generation DISABLED in production flow

**Why Disabled**:
- Complex algorithm requiring accurate birth city
- City matching issues (8,000+ cities)
- Hardcoded instead: "NWTSCI80A01F205A"

**When Enabled**:
- Requires: name, surname, birth_date, gender, birth_city
- Uses fuzzy matching on city names
- Calls `calculate_tax_code()` from extractCF.py
- Returns 16-character code

**Current Logic** (in patient_detail_handlers.py):
```python
if patient_found_in_db:
    fiscal_code = flow_manager.state.get("generated_fiscal_code")
else:
    fiscal_code = "NWTSCI80A01F205A"  # Hardcoded for new patients
```

---

## Error Handling & Recovery

### Error Node Pattern
**Location**: `flows/nodes/completion.py`

**Function**: `create_error_node(error_message)`
- Displays error to user
- Offers to restart booking
- Logs error with context

### Common Error Scenarios

**1. Service Search Failures**:
- No results: `create_search_retry_node()` - Ask for full service name
- API error: Falls back to local_data_service
- Timeout: Retry with user feedback

**2. Center Search Failures**:
- No centers: `create_no_centers_node()` - Suggest different location
- API error: `create_error_node()` - Restart
- Missing patient info: Collect missing data

**3. Slot Search Failures**:
- No slots: `create_no_slots_node()` - Suggest different date
- Time filter too narrow: Expand to full day
- API timeout: Retry

**4. Booking Creation Failures**:
- Validation error: Show specific field error
- Slot conflict (409): "Time no longer available"
- Auth error (401): Refresh token and retry
- Missing data: `create_error_node()` with field list

### Retry Mechanisms

**Token Refresh**: Automatic on 401 errors
**Search Retry**: User can refine search term
**Date Retry**: User can choose different date
**Slot Refresh**: Can refresh same-day slots

---

## Security & Compliance

### GDPR Compliance

**2-Month Data Retention**:
- Azure Blob Storage: Auto-delete after 60 days
- Azure MySQL: Manual cleanup via cron job
- Local logs: 7-day rotation

**Data Stored**:
- Call transcripts
- Patient information (name, phone, email, fiscal code)
- Booking details
- Audio recordings
- Authorizations (reminder, marketing)

### Security Measures

**Non-Root Container**:
- User: pipecat:pipecat
- Group: pipecat
- Ownership: /app and /opt/torch

**API Key Management**:
- All keys in .env file
- Not committed to Git (.gitignore)
- Environment variable injection

**Authentication**:
- OAuth2 Bearer tokens
- Automatic token refresh
- 5-minute expiry buffer

**CORS**:
- Allowed origins: All (*)
- Required for WebSocket connections

---

## Known Issues & Limitations

### 1. **Docker Build Time: 4-6 Hours**
**Root Cause**:
- PyTorch downloads (~800MB)
- TorchAudio downloads (~100MB)
- Silero VAD model downloads (~100MB)
- Native dependency compilation

**Impact**:
- Slow deployment cycles
- Cannot quickly fix bugs
- Extended downtime
- Developer frustration

### 2. **Single Container Per Call**
**Current Limitation**:
- One uvicorn worker
- Stateful session management
- No horizontal scaling

**Required Changes**:
- Container orchestration (Kubernetes/ECS)
- Session externalization (Redis)
- Load balancing
- Auto-scaling policies

### 3. **No Health Check in docker-compose**
- Health check defined in Dockerfile
- Not configured in docker-compose.yml
- No automatic restart on failure

### 4. **Manual Scaling**
- Must manually start new containers
- No auto-scaling triggers
- No load distribution

### 5. **Hardcoded Fiscal Code**
- Uses "NWTSCI80A01F205A" for new patients
- Real generation disabled
- May cause issues with Cerba API validation

### 6. **STT Switching Disabled**
- Email mode switching commented out
- Uses Nova-3 general for everything
- May affect email transcription accuracy

---

## Project Metrics Summary

**Codebase**:
- Files: 65
- Lines: 30,969
- Languages: Python (primary), Text (configs)
- Functions: 289
- Classes: 50
- Dependencies: 685 imports
- No Circular Dependencies

**Docker**:
- Image Size: ~3-4GB
- Build Time: 4-6 hours
- Layers: 7 stages
- Base Image: python:3.11-slim

**Conversation Flow**:
- Nodes: 18 creator functions
- Handlers: 45 functions across 6 files
- States: 50+ different flow states
- Average conversation: 10-25 node transitions

**APIs Integrated**:
- Cerba Healthcare API (4 endpoints)
- Deepgram STT
- ElevenLabs TTS
- OpenAI LLM
- Twilio SMS
- Azure Blob Storage
- Azure MySQL
- Redis Cache

**Data**:
- Services: ~8,000 in local database
- Cities: ~8,000 Italian cities
- Patients: 3 test patients in memory

---

## Optimization Opportunities Identified

### 1. Docker Build Optimization
**Current**: Full rebuild = 4-6 hours

**Potential Solutions**:
- Pre-built base images with PyTorch
- Remote layer caching
- BuildKit cache mounts
- Multi-architecture builds

### 2. Container Orchestration
**Current**: Single container, manual scaling

**Needed**:
- Kubernetes deployment
- Horizontal Pod Autoscaler (HPA)
- Service mesh for load balancing
- Persistent session storage (Redis)

### 3. Deployment Pipeline
**Current**: Manual deploy.sh script

**Potential**:
- CI/CD with GitHub Actions
- Automated testing before deploy
- Gradual rollout strategies
- Health-check based deployment

### 4. Resource Optimization
**Current**: 1GB RAM per container

**Potential**:
- Shared model volume (NFS/EFS)
- Lighter VAD alternative
- CPU-only PyTorch (no CUDA)

---

## Development Workflow Summary

### Recommended Development Process

**90% of Development** - Text Mode:
```bash
python chat_test.py                # Fast iteration
python chat_test.py --start-node booking  # Test specific flows
```

**10% of Development** - Voice Mode:
```bash
python test.py                     # Final validation
python test.py --start-node email  # Voice testing
```

**Benefits**:
- 10x faster testing
- Lower API costs
- Better debugging
- Identical flow logic

### Code Change Process

1. **Modify Code**: Edit flows/handlers/services
2. **Test Text**: `python chat_test.py` for rapid validation
3. **Test Voice**: `python test.py` for final check
4. **Commit**: Git commit changes
5. **Build**: `./deploy.sh` (4-6 hours!)
6. **Deploy**: Azure VM pull and restart

**Pain Point**: Step 5 (Docker build) blocks rapid iteration

---

## Architecture Recommendations for Scalability

### Target Requirements
- **Concurrent Calls**: 15-20 simultaneous
- **Daily Volume**: 500-600 calls
- **Response Time**: <1 second per interaction
- **Availability**: 99.9% uptime

### Required Changes

**1. Container Orchestration**:
- Kubernetes cluster or AWS ECS
- Auto-scaling based on active sessions
- Load balancer for WebSocket connections
- Health checks and automatic recovery

**2. Session Management**:
- External session storage (Redis cluster)
- Stateless containers
- Session affinity in load balancer

**3. Build Optimization**:
- Pre-built base images
- Layer caching in CI/CD
- Incremental builds
- Multi-stage optimization

**4. Monitoring**:
- Call metrics (duration, success rate)
- Container health
- API latency tracking
- Error rate monitoring

---

**Last Updated**: 2025-11-01 