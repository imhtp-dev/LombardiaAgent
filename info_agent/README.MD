# Info Agent - Ualà (Medical Information Assistant)

**Agent Name**: Ualà  
**Framework**: Pipecat AI  
**Organization**: Cerba HealthCare Group (Piedmont Region)  
**Language**: Italian  
**Purpose**: Medical information assistant that provides information WITHOUT booking appointments  

---

## Overview

The Info Agent is a voice-based AI assistant that answers medical information queries about Cerba Healthcare services. It uses the same infrastructure as the booking agent but focuses on providing information rather than booking appointments.

### Key Features

✅ Knowledge base queries (FAQs, documents, forms)  
✅ Competitive/non-Agonisticavisit pricing  
✅ Exam requirements by visit type or sport  
✅ Clinic information (hours, closures, blood collection times)  
✅ Transfer to human operator when needed  
✅ Italian language optimized  
✅ Natural conversation flow  

### Restrictions

❌ Cannot book appointments (offers transfer instead)  
❌ Cannot provide medical advice  
❌ Cannot answer SSN/Agreement questions  
❌ Never uses own knowledge (only functions/APIs)  

---

## Architecture

### Services Stack

```
User (Phone/Browser)
    ↓
Transport (WebSocket/WebRTC)
    ↓
Pipecat Pipeline:
  - Deepgram STT (Italian)
  - OpenAI GPT-4.1-mini
  - ElevenLabs TTS (Italian)
    ↓
Pipecat Flows (Dynamic)
    ↓
External APIs:
  - Knowledge Base
  - Pricing APIs
  - Exam Lists
  - Clinic Info
```

### File Structure

```
info_agent/
├── main.py                      # FastAPI server (port 8081)
├── chat_test.py                 # Text testing (port 8082)
├── config/
│   ├── __init__.py
│   └── settings.py              # Configuration
├── services/
│   ├── __init__.py
│   ├── knowledge_base.py        # Knowledge base API
│   ├── pricing_service.py       # Pricing APIs
│   ├── exam_service.py          # Exam list APIs
│   └── clinic_info_service.py   # Clinic info API
├── flows/
│   ├── __init__.py
│   ├── manager.py               # Flow initialization
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── greeting.py          # Initial greeting with all tools
│   │   ├── answer.py            # Post-answer follow-up
│   │   └── transfer.py          # Transfer to human
│   └── handlers/
│       ├── __init__.py
│       ├── knowledge_handlers.py    # KB queries
│       ├── pricing_handlers.py      # Pricing queries
│       ├── exam_handlers.py         # Exam list queries
│       ├── clinic_handlers.py       # Clinic info queries
│       └── transfer_handlers.py     # Transfer logic
└── pipeline/
    └── __init__.py
```

---

## Installation

### Prerequisites

Same as booking agent:
- Python 3.11
- All dependencies from parent `requirements.txt`
- API keys for Deepgram, OpenAI, ElevenLabs

### Environment Variables

Add to your `.env` file:

```bash
# Info Agent Configuration
INFO_AGENT_PORT=8081
INFO_AGENT_HOST=0.0.0.0

# Knowledge Base API
KNOWLEDGE_BASE_URL=

# Exam APIs
EXAM_BY_VISIT_URL=
EXAM_BY_SPORT_URL=

# Pricing APIs
PRICE_NON_AGONISTIC_URL=
PRICE_AGONISTIC_URL=

# Clinic Info API
CALL_GRAPH_URL=

# API Timeout (optional)
API_TIMEOUT=30
```

---

## Usage

### Running the Voice Agent (Production)

```bash
# From project root
cd info_agent
python main.py
```

Agent runs on port **8081** (configurable via `INFO_AGENT_PORT`)

**Endpoints**:
- `GET /` - Homepage with agent information
- `GET /health` - Health check
- `WS /ws` - WebSocket endpoint for audio

**WebSocket Parameters**:
```
ws://localhost:8081/ws?session_id=xxx&caller_phone=+39xxx&start_node=greeting
```

### Running the Chat Test Interface (Development)

```bash
# From project root
cd info_agent
python chat_test.py
```

Test interface runs on port **8082**

**Access**: Open http://localhost:8082 in browser

**Benefits**:
- ✅ No STT/TTS API costs
- ✅ Instant responses (10x faster than voice)
- ✅ Same flow logic as production
- ✅ Browser-based UI
- ✅ Perfect for testing conversation flows

---

## Available Functions (Tools)

### 1. Knowledge Base Query

```python
query_knowledge_base(query: str)
```

**Purpose**: Search knowledge base for FAQs, documents, forms  
**Example**: "Quali documenti servono per la visita sportiva?"  
**Transitions to**: Answer Node  

### 2. AgonisticaVisit Pricing

```python
get_competitive_visit_price(age: int, gender: str, sport: str, region: str)
```

**Purpose**: Get price for Agonistica(agonistic) visit  
**Parameters**:
- `age`: Patient age (integer)
- `gender`: "M" or "F"
- `sport`: Sport name in Italian
- `region`: Italian region

**Example**: "Quanto costa una visita agonistica per calcio?"  
**Transitions to**: Answer Node  

### 3. Non-AgonisticaVisit Pricing

```python
get_non_competitive_visit_price(ecg_under_stress: bool)
```

**Purpose**: Get price for non-Agonisticavisit  
**Parameters**:
- `ecg_under_stress`: True if ECG under stress needed

**Example**: "Quanto costa una visita non agonistica?"  
**Transitions to**: Answer Node  

### 4. Exam List by Visit Type

```python
get_exam_list_by_visit_type(visit_type: str)
```

**Purpose**: Get exam requirements for visit type  
**Parameters**:
- `visit_type`: One of A1, A2, A3, B1, B2, B3, B4, B5

**Example**: "Quali esami servono per la visita tipo A1?"  
**Transitions to**: Answer Node  

### 5. Exam List by Sport

```python
get_exam_list_by_sport(sport: str)
```

**Purpose**: Get exam requirements for specific sport  
**Parameters**:
- `sport`: Sport name in Italian

**Example**: "Quali esami servono per il calcio?"  
**Transitions to**: Answer Node  

### 6. Clinic Information

```python
get_clinic_info(location: str, info_type: str)
```

**Purpose**: Get clinic hours, closures, blood collection times  
**Parameters**:
- `location`: City/location (e.g., "Novara", "Biella")
- `info_type`: Type of info (e.g., "summer closures", "blood collection times")

**Example**: "Avete chiusure estive a Novara?"  
**Note**: Bot must ask for location first  
**Transitions to**: Answer Node  

### 7. Request Transfer

```python
request_transfer(reason: str)
```

**Purpose**: Transfer to human operator  
**Parameters**:
- `reason`: Why transfer is needed

**When used**:
- User wants to book appointment
- Cannot find answer in knowledge base
- User explicitly requests transfer
- SSN/Agreement questions

**Transitions to**: Transfer Node → End  

---

## Conversation Flow

### Flow Diagram

```
Start
  ↓
Greeting Node (Bot speaks first)
  ↓
User Query
  ↓
[LLM Classifies Intent]
  ↓
┌─────────────────┬─────────────────┬─────────────────┐
│   Knowledge     │    Pricing      │   Exam List     │  etc.
│   Base Query    │    Query        │   Query         │
└────────┬────────┴────────┬────────┴────────┬────────┘
         ↓                 ↓                  ↓
    Answer Node       Answer Node        Answer Node
         ↓                 ↓                  ↓
    [Check Follow-up]
         ↓
    ┌────┴────┐
    ↓         ↓
More Help?  Done
    ↓         ↓
 Greeting   Goodbye
```

### Node Descriptions

**Greeting Node**:
- Bot speaks first: "Ciao, sono Ualà..."
- All 7 functions available
- Routes based on user intent

**Answer Node**:
- Provides information
- Asks if user needs more help
- Functions: `check_followup`, `request_transfer`

**Transfer Node**:
- Informs user of transfer
- Ends conversation
- Escalation logic triggered

**Goodbye Node**:
- Thanks user
- Ends conversation gracefully

---

## Testing

### Chat Test (Recommended for Development)

```bash
cd info_agent
python chat_test.py 
`or`
info_agent\test_info_agent.py

```

Then open: http://localhost:8082

**Test Scenarios**:

1. **Knowledge Base Query**:
   ```
   You: "Ciao, quali sono le preparazioni per gli esami del sangue?"
   Ualà: [Searches KB] "Per gli esami del sangue..."
   ```

2. **AgonisticaPricing**:
   ```
   You: "Quanto costa una visita agonistica?"
   Ualà: "Per darti il prezzo, ho bisogno di alcune informazioni. Quanti anni hai?"
   You: "15"
   Ualà: "Sei maschio o femmina?"
   You: "Maschio"
   Ualà: "Quale sport pratichi?"
   You: "Calcio"
   Ualà: "In quale regione?"
   You: "Piemonte"
   Ualà: [Gets price] "Il prezzo è €XX"
   ```

3. **Clinic Hours**:
   ```
   You: "Avete chiusure estive?"
   Ualà: "In quale sede vuoi sapere se ci sono chiusure estive?"
   You: "Novara"
   Ualà: [Gets info] "A Novara..."
   ```

4. **Transfer Request**:
   ```
   You: "Voglio prenotare un appuntamento"
   Ualà: "Per prenotazioni, posso trasferirt a un collega. Vuoi essere trasferito?"
   You: "Sì"
   Ualà: [Transfers]
   ```

### Voice Test (After Chat Testing)

```bash
cd info_agent
python main.py
```

Connect via WebSocket client or Talkdesk bridge.

---

## Integration with Booking Agent

### Current State

- **Info Agent**: Port 8081 (standalone)
- **Booking Agent**: Port 8000 (existing)
- **Shared**: All AI services, Azure infrastructure

### Future Router Integration

```python
# router.py (to be implemented)
async def route_call(initial_intent):
    if "prenotare" in intent or "appuntamento" in intent:
        # Route to booking agent
        connect_to_agent("booking", port=8000)
    else:
        # Route to info agent
        connect_to_agent("info", port=8081)
```

### Shared Infrastructure

Both agents share:
- Deepgram STT (Italian, Nova-3)
- OpenAI GPT-4.1-mini
- ElevenLabs TTS (Italian voice)
- Azure MySQL (call logging)
- Azure Blob Storage (transcripts)
- Redis Cache (session management)
- Silero VAD

---

## Development Workflow

### 1. Make Changes

Edit handlers, nodes, or services as needed.

### 2. Test with Chat Interface

```bash
python chat_test.py
# Open http://localhost:8082
# Test conversation flows
```





**10% final validation** with voice:
- Validate Italian language
- Test interruptions
- Check latency
- Validate end-to-end

### 4. Deploy

Same Docker configuration as booking agent.

---

## API Integration

### Knowledge Base

**Endpoint**: `/query_new`  
**Method**: POST  
**Body**: `{"query": "user question"}`  
**Response**: `{"answer": "...", "confidence": 0.9, "source": "..."}`  

### Pricing - Competitive

**Endpoint**: `/get_price_agonistic_visit`  
**Method**: POST  
**Body**: `{"age": 15, "gender": "M", "sport": "calcio", "region": "Piemonte"}`  
**Response**: `{"price": 75.0, "visit_type": "A1"}`  

### Pricing - Non-Competitive

**Endpoint**: `/get_price_non_agonistic_visit`  
**Method**: POST  
**Body**: `{"ecg_under_stress": false}`  
**Response**: `{"price": 50.0}`  

### Exam List - By Visit

**Endpoint**: `/get_list_exam_by_visit`  
**Method**: POST  
**Body**: `{"visit_type": "A1"}`  
**Response**: `{"exams": ["ECG", "Spirometry", "..."]}`  

### Exam List - By Sport

**Endpoint**: `/get_list_exam_by_sport`  
**Method**: POST  
**Body**: `{"sport": "calcio"}`  
**Response**: `{"exams": ["ECG", "Spirometry", "..."]}`  

### Clinic Info

**Endpoint**: `/call_graph`  
**Method**: POST  
**Body**: `{"q": "summer closures, Novara location"}`  
**Response**: `{"answer": "..."}`  

---

## Troubleshooting

### Common Issues

#### 1. Import Errors

**Problem**: `ModuleNotFoundError: No module named 'info_agent'`

**Solution**: Run from project root:
```bash
cd pipecat-booking-agent
python -m info_agent.main
python -m info_agent.chat_test
```

#### 2. API Timeout

**Problem**: "Knowledge base query timeout"

**Solution**: Increase timeout in `.env`:
```bash
API_TIMEOUT=60
```

#### 3. Missing API Keys

**Problem**: "DEEPGRAM_API_KEY not found"

**Solution**: Ensure all keys in `.env`:
```bash
DEEPGRAM_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
OPENAI_API_KEY=your_key
```

#### 4. Port Already in Use

**Problem**: "Address already in use: 8081"

**Solution**: Change port in `.env`:
```bash
INFO_AGENT_PORT=8083
```

Or kill existing process:
```bash
# Windows
netstat -ano | findstr :8081
taskkill /PID <pid> /F
```

---

## Performance

### Expected Latency

- **Chat Test**: <100ms (no STT/TTS)
- **Voice (FastAPI WebSocket)**: 500-800ms
- **API Calls**: 
  - Knowledge Base: 1-3 seconds
  - Pricing: <1 second
  - Exam Lists: <1 second
  - Clinic Info: 1-2 seconds

### Optimization Tips

1. **Use Chat Test** for 90% of development
2. **Cache common queries** (future enhancement)
3. **Monitor API latency** via logs
4. **Use parallel API calls** when possible

---



## Documentation

- **Implementation Summery**: [`IMPLEMENTATION_SUMMARY.md`](IMPLEMENTATION_SUMMARY.md) - Detailed architecture


