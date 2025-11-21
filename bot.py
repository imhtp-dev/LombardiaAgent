import os
import re
import asyncio
import wave
import time
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv
from loguru import logger

# Enable Deepgram and WebSocket debugging
logging.getLogger("deepgram").setLevel(logging.DEBUG)
logging.getLogger("websockets").setLevel(logging.DEBUG)

# FastAPI
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Core Pipecat imports
from pipecat.frames.frames import (
    TranscriptionFrame,
    InterimTranscriptionFrame,
    Frame,
    TTSSpeakFrame,
    LLMMessagesFrame,
    InputAudioRawFrame,
    OutputAudioRawFrame,
    MetricsFrame
)
from pipecat.processors.transcript_processor import TranscriptProcessor
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.observers.base_observer import BaseObserver
from pipecat.metrics.metrics import LLMUsageMetricsData

from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

from pipecat.audio.vad.silero import SileroVADAnalyzer, VADParams

# Serializer imports 
from pipecat.serializers.base_serializer import FrameSerializer, FrameSerializerType

# Import flow management
from flows.manager import create_flow_manager, initialize_flow_manager

from config.settings import settings
from services.config import config
from pipeline.components import create_stt_service, create_tts_service, create_llm_service, create_context_aggregator

# Import transcript manager for conversation recording and call data extraction
from services.transcript_manager import get_transcript_manager, cleanup_transcript_manager

load_dotenv(override=True)

# SIMPLE PCM SERIALIZER
class RawPCMSerializer(FrameSerializer):
    """
    Simple serializer for PCM raw (EXACTLY LIKE APP.PY)
    """

    @property
    def type(self):
        return FrameSerializerType.BINARY

    async def serialize(self, frame: Frame) -> bytes:
        """Serialize outgoing audio frames"""
        if isinstance(frame, OutputAudioRawFrame):
            return frame.audio
        return b''

    async def deserialize(self, data) -> Frame:
        """Deserialize incoming PCM raw"""
        if isinstance(data, bytes) and len(data) > 0:
            return InputAudioRawFrame(
                audio=data,
                sample_rate=16000,
                num_channels=1
            )
        return None


class LLMUsageMetricsObserver(BaseObserver):
    """
    Observer to capture LLM token usage metrics and increment call_extractor token count.
    Monitors MetricsFrame for LLMUsageMetricsData and updates the token counter.
    """

    def __init__(self, flow_manager):
        super().__init__()
        self.flow_manager = flow_manager
        logger.info("🔢 LLMUsageMetricsObserver initialized")

    async def on_push_frame(
        self,
        src: FrameProcessor,
        dst: FrameProcessor,
        frame: Frame,
        direction: FrameDirection,
        timestamp: int,
    ):
        """Capture LLM usage metrics when MetricsFrame is pushed"""
        # Check if this is a MetricsFrame
        if isinstance(frame, MetricsFrame):
            # Iterate through metrics data
            for metric in frame.data:
                # Check if this is LLM usage metrics
                if isinstance(metric, LLMUsageMetricsData):
                    usage = metric.value
                    total_tokens = usage.total_tokens

                    logger.info(f"🔢 LLM Token Usage Captured:")
                    logger.info(f"   Processor: {metric.processor}")
                    logger.info(f"   Model: {metric.model}")
                    logger.info(f"   Prompt tokens: {usage.prompt_tokens}")
                    logger.info(f"   Completion tokens: {usage.completion_tokens}")
                    logger.info(f"   Total tokens: {total_tokens}")

                    # Increment call_extractor token count
                    call_extractor = self.flow_manager.state.get("call_extractor")
                    if call_extractor:
                        call_extractor.increment_tokens(total_tokens)
                        logger.info(f"✅ Updated call_extractor total tokens: {call_extractor.llm_token_count}")
                    else:
                        logger.warning("⚠️ call_extractor not found in flow_manager.state")


async def report_to_talkdesk(flow_manager, call_extractor):
    """
    Report call completion to Talkdesk (ONLY if not transferred to human operator).

    Args:
        flow_manager: FlowManager instance with state
        call_extractor: CallDataExtractor instance with call data

    Returns:
        bool: True if successfully sent to Talkdesk, False otherwise
    """
    try:
        # Check 1: Was call transferred to human operator?
        if flow_manager.state.get("transfer_requested"):
            logger.info("⏭️ Skipping Talkdesk report - call was transferred to human operator")
            return False

        # Check 2: Do we have interaction_id?
        interaction_id = flow_manager.state.get("interaction_id")
        if not interaction_id:
            logger.warning("⚠️ No interaction_id - cannot report to Talkdesk")
            return False

        logger.info(f"📤 Preparing Talkdesk report for interaction: {interaction_id}")

        # Get analysis data (reuse if available from transfer preparation)
        analysis = flow_manager.state.get("transfer_analysis")

        if not analysis:
            logger.info("🔍 No pre-computed analysis, running LLM analysis for Talkdesk report")
            transcript_text = call_extractor._generate_transcript_text()
            analysis = await call_extractor._analyze_call_with_llm(
                transcript_text,
                flow_manager.state
            )
        else:
            logger.info("✅ Using pre-computed analysis from transfer preparation")

        # Build Talkdesk payload
        call_data = {
            "interaction_id": interaction_id,
            "sentiment": analysis.get("sentiment", "neutral"),
            "service": str(analysis.get("service", "5")),
            "summary": analysis.get("summary", "")[:250],  # Max 250 chars
            "duration_seconds": int(call_extractor._calculate_duration() or 0)
        }

        logger.info(f"📊 Talkdesk payload prepared:")
        logger.info(f"   Interaction ID: {call_data['interaction_id']}")
        logger.info(f"   Sentiment: {call_data['sentiment']}")
        logger.info(f"   Service: {call_data['service']}")
        logger.info(f"   Duration: {call_data['duration_seconds']}s")
        logger.info(f"   Summary: {call_data['summary'][:100]}...")

        # Send to Talkdesk
        from talkdesk_hangup import send_to_talkdesk
        success = send_to_talkdesk(call_data)

        if success:
            logger.success(f"✅ Talkdesk report sent successfully for interaction: {interaction_id}")
        else:
            logger.error(f"❌ Talkdesk report failed for interaction: {interaction_id}")

        return success

    except Exception as e:
        logger.error(f"❌ Error reporting to Talkdesk: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False


# LIFESPAN CONTEXT MANAGER

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting up Healthcare Flow Bot...")

    # Initialize Supabase database connection for info agent
    try:
        from info_agent.api.database import db
        await db.connect()
        logger.success("✅ Info agent Supabase database initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase database: {e}")
        logger.warning("⚠️ Info agent will use backup files for failed database saves")

    # Initialize Pinecone and OpenAI for Q&A management
    try:
        from info_agent.api.qa import initialize_ai_services
        initialize_ai_services()
        logger.success("✅ AI services (Pinecone + OpenAI) initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize AI services: {e}")
        logger.warning("⚠️ Q&A management will not work without Pinecone")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Healthcare Flow Bot...")

    # Close Supabase database connection
    try:
        from info_agent.api.database import db
        await db.close()
        logger.success("✅ Info agent Supabase database closed")
    except Exception as e:
        logger.error(f"❌ Error closing Supabase database: {e}")


# FASTAPI APP

app = FastAPI(
    title="Healthcare Flow Bot with Working WebSocket",
    description="Healthcare flow bot using app.py WebSocket transport",
    version="5.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== REGISTER API ROUTERS ====================
# Import and register dashboard API routers
from info_agent.api import auth, users, qa, dashboard, chat

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(qa.router, prefix="/api/qa", tags=["Q&A Management"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])

logger.info("✅ Dashboard API routers registered")
logger.info("   - /api/auth/* - Authentication endpoints")
logger.info("   - /api/users/* - User management")
logger.info("   - /api/qa/* - Q&A management")
logger.info("   - /api/dashboard/* - Dashboard statistics")
logger.info("   - /api/chat/* - Chat endpoints")

# Store for active sessions
active_sessions: Dict[str, Any] = {}

# HOMEPAGE 

@app.get("/")
async def root():
    """Homepage with information about the server"""
    return HTMLResponse(f"""
    <html>
        <head>
            <title>Healthcare Flow Bot - Working WebSocket</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    margin: 40px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }}
                .container {{
                    background: rgba(255,255,255,0.95);
                    color: #333;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    max-width: 800px;
                    margin: 0 auto;
                }}
                .status {{
                    color: #22c55e;
                    font-weight: bold;
                }}
                .service {{
                    display: inline-block;
                    padding: 5px 10px;
                    margin: 5px;
                    background: #667eea;
                    color: white;
                    border-radius: 5px;
                    font-size: 12px;
                }}
                h1 {{ color: #333; }}
                h2 {{ color: #667eea; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🏥 Healthcare Flow Bot - Working WebSocket</h1>
                <p class="status">✅ Server is running with app.py WebSocket transport</p>

                <h2>Active Services:</h2>
                <div>
                    <span class="service">Deepgram STT</span>
                    <span class="service">OpenAI GPT-4</span>
                    <span class="service">ElevenLabs TTS</span>
                    <span class="service">Pipecat Flows</span>
                </div>

                <h2>Endpoints:</h2>
                <ul>
                    <li><code>GET /</code> - This page</li>
                    <li><code>GET /health</code> - Health check</li>
                    <li><code>WS /ws</code> - WebSocket endpoint for bridge</li>
                </ul>

                <h2>Statistics:</h2>
                <p>Active sessions: <strong>{len(active_sessions)}</strong></p>
            </div>
        </body>
    </html>
    """)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "service": "healthcare-flow-bot-websocket",
        "version": "5.0.0",
        "active_sessions": len(active_sessions),
        "services": {
            "stt": "deepgram",
            "llm": "openai-gpt4",
            "tts": "elevenlabs",
            "flows": "pipecat-flows",
            "transport": "fastapi-websocket-from-app.py"
        }
    })

# MAIN WEBSOCKET ENDPOINT
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Healthcare Flow Bot WebSocket endpoint
    USES EXACT SAME STRUCTURE AS APP.PY BUT WITH BOT.PY FLOW INTELLIGENCE
    """
    await websocket.accept()

    # Extract parameters from query string
    query_params = dict(websocket.query_params)
    business_status = query_params.get("business_status")  # ✅ NO DEFAULT - Must come from TalkDesk
    import uuid
    session_id = query_params.get("session_id", f"session-{uuid.uuid4().hex[:8]}")
    start_node = query_params.get("start_node", "router")  # Default to unified router
    caller_phone = query_params.get("caller_phone", "")
    stream_sid = query_params.get("stream_sid", "")  # ✅ Talkdesk stream SID (for escalation stop message)
    interaction_id = query_params.get("interaction_id", "")  # ✅ Talkdesk interaction ID (for database tracking)

    logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"New Healthcare Flow WebSocket Connection")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Business Status: {business_status or 'NOT PROVIDED - ERROR!'}")  # ✅ Log clearly if missing
    logger.info(f"Start Node: {start_node}")
    logger.info(f"Caller Phone: {caller_phone or 'Not provided'}")
    logger.info(f"Stream SID: {stream_sid or 'Not provided'}")  # ✅ Talkdesk stream SID (for escalation)
    logger.info(f"Interaction ID: {interaction_id or 'Not provided'}")  # ✅ Talkdesk interaction ID
    logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # ✅ Validate business_status is provided
    if not business_status:
        logger.error("❌ CRITICAL: business_status not provided by TalkDesk bridge!")
        logger.error("   This will cause incorrect transfer behavior")
        business_status = "close"  # Safe fallback - no transfers when unsure
        logger.warning(f"⚠️ Using fallback business_status: {business_status}")

    # Variables for pipeline
    runner = None
    task = None

    try:
        # Check required API keys
        required_keys = [
            ("DEEPGRAM_API_KEY", "Deepgram"),
            ("ELEVENLABS_API_KEY", "ElevenLabs"),
            ("OPENAI_API_KEY", "OpenAI")
        ]

        for key_name, service_name in required_keys:
            if not os.getenv(key_name):
                raise Exception(f"{key_name} not found - required for {service_name}")

        # Validate health service configuration
        try:
            config.validate()
            logger.success("✅ Health services configuration validated")
        except Exception as e:
            logger.error(f"❌ Health services configuration error: {e}")
            raise

        # CREATE TRANSPORT
        transport = FastAPIWebsocketTransport(
            websocket=websocket,
            params=FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                add_wav_header=False,
                vad_analyzer=SileroVADAnalyzer(
                    params=VADParams(
                        start_secs=settings.vad_config["start_secs"],
                        stop_secs=settings.vad_config["stop_secs"],
                        min_volume=settings.vad_config["min_volume"]
                    )
                ),
                serializer=RawPCMSerializer(),  # EXACT SAME AS APP.PY
                session_timeout=900,
                )
            )
        

        # CREATE SERVICES USING BOT.PY COMPONENTS
        logger.info("Initializing services...")
        stt = create_stt_service()

        tts = create_tts_service()
        llm = create_llm_service()
        context_aggregator = create_context_aggregator(llm)

        # CREATE TRANSCRIPT PROCESSOR FOR RECORDING CONVERSATIONS
        transcript_processor = TranscriptProcessor()

        logger.info("✅ All services initialized")

        # CREATE USER IDLE PROCESSOR FOR HANDLING TRANSCRIPTION FAILURES
        from services.idle_handler import create_user_idle_processor
        user_idle_processor = create_user_idle_processor(timeout_seconds=50.0)
        logger.info("🕐 UserIdleProcessor created (50s timeout - accounts for API processing delays)")

        # CREATE PIPELINE WITH TRANSCRIPT PROCESSORS AND IDLE HANDLING
        pipeline = Pipeline([
            transport.input(),
            stt,
            user_idle_processor,                      # Add idle detection after STT
            transcript_processor.user(),              # Capture user transcriptions
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            transcript_processor.assistant(),         # Capture assistant responses
            context_aggregator.assistant()
        ])

        logger.info("Healthcare Flow Pipeline structure:")
        logger.info("  1. Input (PCM from bridge)")
        logger.info("  2. Deepgram STT")
        logger.info("  3. UserIdleProcessor - Handle transcription failures & silence")
        logger.info("  4. TranscriptProcessor.user() - Capture user transcriptions")
        logger.info("  5. Context Aggregator (User)")
        logger.info("  6. OpenAI LLM (with flows + gender node termina→femmina correction)")
        logger.info("  7. ElevenLabs TTS")
        logger.info("  8. Output (PCM to bridge)")
        logger.info("  9. TranscriptProcessor.assistant() - Capture assistant responses")
        logger.info("  10. Context Aggregator (Assistant)")

        # START PER-CALL LOGGING (create individual logger instance)
        from services.call_logger import CallLogger
        session_call_logger = CallLogger(session_id)
        log_file = session_call_logger.start_call_logging(session_id, caller_phone)
        logger.info(f"📁 Call logging started: {log_file}")

        # CREATE FLOW MANAGER (TEMPORARY - will be updated with task later)
        # We need a placeholder flow_manager for the observer during initialization
        flow_manager_placeholder = type('obj', (object,), {'state': {}})()  # Minimal placeholder with state dict

        # Create LLM token usage observer with placeholder
        token_observer = LLMUsageMetricsObserver(flow_manager_placeholder)

        # Create pipeline task with extended idle timeout for API calls and token tracking enabled
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_transcriptions=True,
                audio_in_sample_rate=16000,
                audio_out_sample_rate=16000,
                enable_usage_metrics=True,  # ✅ ENABLE TOKEN TRACKING
            ),
            observers=[token_observer],  # ✅ ATTACH OBSERVER
            idle_timeout_secs=600  # 10 minutes - allows for long API calls (sorting, slot search)
        )

        # NOW create the real FlowManager with all parameters
        flow_manager = create_flow_manager(task, llm, context_aggregator, transport)

        # Update observer to use the real flow_manager
        token_observer.flow_manager = flow_manager

        # ✅ Store business_status, session_id, and stream_sid in flow manager state
        flow_manager.state["business_status"] = business_status
        flow_manager.state["session_id"] = session_id
        flow_manager.state["stream_sid"] = stream_sid  # ✅ Talkdesk stream SID for escalation
        flow_manager.state["interaction_id"] = interaction_id  # ✅ Talkdesk interaction ID for database
        logger.info(f"✅ Business status stored in flow state: {business_status}")
        logger.info(f"✅ Session ID stored in flow state: {session_id}")
        logger.info(f"✅ Stream SID stored in flow state: {stream_sid or 'Not provided'}")
        logger.info(f"✅ Interaction ID stored in flow state: {interaction_id or 'Not provided'}")

        # Store caller phone number in flow manager state
        if caller_phone:
            flow_manager.state["caller_phone_from_talkdesk"] = caller_phone
            session_call_logger.log_phone_debug("PHONE_STORED_IN_FLOW_STATE", {
                "caller_phone": caller_phone,
                "session_id": session_id,
                "business_status": business_status,
                "flow_state_keys": list(flow_manager.state.keys())
            })

            # Also store in Azure storage for persistence
            try:
                from services.call_storage import CallDataStorage
                storage = CallDataStorage()
                await storage.store_caller_phone(session_id, caller_phone)
                logger.success(f"✅ Caller phone stored in Azure: {caller_phone}")
            except Exception as e:
                logger.error(f"❌ Failed to store caller phone in Azure: {e}")

        # Initialize STT switcher for dynamic transcription
        from utils.stt_switcher import initialize_stt_switcher
        initialize_stt_switcher(stt, flow_manager)

        # Setup transcript recording event handler (must be AFTER flow_manager creation)
        @transcript_processor.event_handler("on_transcript_update")
        async def on_transcript_update(processor, frame):
            """Handle transcript updates from TranscriptProcessor"""
            logger.info(f"📝 Transcript update received with {len(frame.messages)} messages")

            # Get session-specific transcript manager (for booking agent)
            session_transcript_manager = get_transcript_manager(session_id)

            for message in frame.messages:
                logger.info(f"📝 Recording {message.role} message: '{message.content[:50]}{'...' if len(message.content) > 50 else ''}'")

                # Always add to transcript_manager (needed for both agents)
                if message.role == "user":
                    session_transcript_manager.add_user_message(message.content)
                elif message.role == "assistant":
                    session_transcript_manager.add_assistant_message(message.content)

                # ALSO add to call_extractor (ALWAYS - Lombardy mode uses info agent only)
                call_extractor_instance = flow_manager.state.get("call_extractor")
                if call_extractor_instance:
                    call_extractor_instance.add_transcript_entry(message.role, message.content)
                    logger.debug(f"📊 Added to call_extractor: {message.role}")

            logger.info(f"📊 Transcript now has {len(session_transcript_manager.conversation_log)} messages")

        # EVENT HANDLERS
        # Transport event handlers
        @transport.event_handler("on_client_connected")
        async def on_client_connected(transport_obj, ws):
            logger.info(f"✅ Healthcare Flow Client connected: {session_id}")
            active_sessions[session_id] = {
                "websocket": ws,
                "business_status": business_status,
                "connected_at": asyncio.get_event_loop().time(),
                "call_logger": session_call_logger,  # Store per-session logger
                "services": {
                    "stt": "deepgram",
                    "llm": "openai-gpt4-flows",
                    "tts": "elevenlabs",
                    "flows": "pipecat-flows"
                }
            }

            # Start transcript recording session
            session_transcript_manager = get_transcript_manager(session_id)
            session_transcript_manager.start_session(session_id)
            logger.info(f"📝 Started transcript recording for session: {session_id}")
            logger.info(f"📊 Transcript manager initialized with {len(session_transcript_manager.conversation_log)} messages")

            # Initialize call_extractor for info agent (EARLY - to capture ALL messages including router)
            from info_agent.services.call_data_extractor import get_call_extractor
            call_extractor = get_call_extractor(session_id)
            call_extractor.call_id = session_id  # Override with session_id from bridge
            call_extractor.interaction_id = interaction_id  # Store Talkdesk interaction ID
            flow_manager.state["call_extractor"] = call_extractor
            logger.info(f"📊 Call extractor initialized for info agent (will capture all messages)")

            # Initialize flow manager
            try:
                await initialize_flow_manager(flow_manager, start_node)
                logger.success(f"✅ Flow initialized with {start_node} node")
            except Exception as e:
                logger.error(f"Error during flow initialization: {e}")

        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport_obj, ws):
            logger.info(f"🔌 Healthcare Flow Client disconnected: {session_id}")

            # Extract and store call data before cleanup
            # Route to appropriate storage based on which agent handled the call
            try:
                current_agent = flow_manager.state.get("current_agent", "unknown")
                logger.info(f"📊 Extracting call data for session: {session_id} | Agent: {current_agent}")

                if current_agent == "info":
                    # INFO AGENT: Use Supabase storage via call_data_extractor
                    logger.info("🟠 INFO AGENT call - routing to Supabase storage")

                    call_extractor = flow_manager.state.get("call_extractor")
                    if call_extractor:
                        # ✅ CRITICAL: Mark call end time before saving
                        call_extractor.end_call()
                        success = await call_extractor.save_to_database(flow_manager.state)
                        if success:
                            logger.success(f"✅ Info agent call data saved to Supabase for session: {session_id}")

                            # Report to Talkdesk (only if not transferred to human operator)
                            await report_to_talkdesk(flow_manager, call_extractor)
                        else:
                            logger.error(f"❌ Failed to save info agent call data to Supabase: {session_id}")
                    else:
                        logger.error("❌ No call_extractor found in flow_manager.state for info agent")

                else:
                    # BOOKING AGENT (or unknown/router): Use Azure Blob Storage via transcript_manager
                    logger.info(f"🟢 BOOKING AGENT call - routing to Azure Blob Storage")

                    session_transcript_manager = get_transcript_manager(session_id)
                    success = await session_transcript_manager.extract_and_store_call_data(flow_manager)
                    if success:
                        logger.success(f"✅ Booking agent call data saved to Azure for session: {session_id}")
                    else:
                        logger.error(f"❌ Failed to save booking agent call data to Azure: {session_id}")

            except Exception as e:
                logger.error(f"❌ Error during call data extraction: {e}")
                import traceback
                traceback.print_exc()

            # Clear transcript session and cleanup
            cleanup_transcript_manager(session_id)

            # Cleanup
            if session_id in active_sessions:
                del active_sessions[session_id]

            await task.cancel()

        @transport.event_handler("on_session_timeout")
        async def on_session_timeout(transport_obj, ws):
            logger.warning(f"⏱️ Session timeout: {session_id}")

            # Extract and store call data before cleanup (even on timeout)
            # Route to appropriate storage based on which agent handled the call
            try:
                current_agent = flow_manager.state.get("current_agent", "unknown")
                logger.info(f"📊 Extracting call data for timed-out session: {session_id} | Agent: {current_agent}")

                if current_agent == "info":
                    # INFO AGENT: Use Supabase storage via call_data_extractor
                    logger.info("🟠 INFO AGENT call (timeout) - routing to Supabase storage")

                    call_extractor = flow_manager.state.get("call_extractor")
                    if call_extractor:
                        success = await call_extractor.save_to_database(flow_manager.state)
                        if success:
                            logger.success(f"✅ Info agent call data saved to Supabase (timeout): {session_id}")

                            # Report to Talkdesk (only if not transferred to human operator)
                            await report_to_talkdesk(flow_manager, call_extractor)
                        else:
                            logger.error(f"❌ Failed to save info agent call data to Supabase (timeout): {session_id}")
                    else:
                        logger.error("❌ No call_extractor found in flow_manager.state for info agent (timeout)")

                else:
                    # BOOKING AGENT (or unknown/router): Use Azure Blob Storage via transcript_manager
                    logger.info(f"🟢 BOOKING AGENT call (timeout) - routing to Azure Blob Storage")

                    session_transcript_manager = get_transcript_manager(session_id)
                    success = await session_transcript_manager.extract_and_store_call_data(flow_manager)
                    if success:
                        logger.success(f"✅ Booking agent call data saved to Azure (timeout): {session_id}")
                    else:
                        logger.error(f"❌ Failed to save booking agent call data to Azure (timeout): {session_id}")

            except Exception as e:
                logger.error(f"❌ Error during timeout call data extraction: {e}")
                import traceback
                traceback.print_exc()

            # Clear transcript session and cleanup
            cleanup_transcript_manager(session_id)

            # Cleanup
            if session_id in active_sessions:
                del active_sessions[session_id]

            await task.cancel()

        # START PIPELINE
        runner = PipelineRunner()

        logger.info(f"🚀 Healthcare Flow Pipeline started for session: {session_id}")
        logger.info(f"🏥 Intelligent conversation flows ACTIVE")

        # Run pipeline (blocks until disconnection)
        await runner.run(task)

    except WebSocketDisconnect:
        logger.info(f"Healthcare Flow WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"❌ Error in Healthcare Flow WebSocket handler: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Extract and store call data before cleanup
        # Route to appropriate storage based on which agent handled the call
        # DUPLICATE LOGIC: Also in event handlers, but MUST be in finally block too
        # because event handlers don't always fire (e.g., escalation transfers)
        try:
            current_agent = flow_manager.state.get("current_agent", "unknown")
            logger.info(f"📊 [FINALLY BLOCK] Extracting call data for session: {session_id} | Agent: {current_agent}")

            if current_agent == "info":
                # INFO AGENT: Use Supabase storage via call_data_extractor
                logger.info("🟠 [FINALLY BLOCK] INFO AGENT call - routing to Supabase storage")

                call_extractor = flow_manager.state.get("call_extractor")
                if call_extractor:
                    # ✅ CRITICAL: Mark call end time before saving
                    call_extractor.end_call()
                    success = await call_extractor.save_to_database(flow_manager.state)
                    if success:
                        logger.success(f"✅ [FINALLY BLOCK] Info agent call data saved to Supabase for session: {session_id}")

                        # Report to Talkdesk (only if not transferred to human operator)
                        await report_to_talkdesk(flow_manager, call_extractor)
                    else:
                        logger.error(f"❌ [FINALLY BLOCK] Failed to save info agent call data to Supabase: {session_id}")
                else:
                    logger.error("❌ [FINALLY BLOCK] No call_extractor found in flow_manager.state for info agent")

            else:
                # BOOKING AGENT (or unknown/router): Use Azure Blob Storage via transcript_manager
                logger.info(f"🟢 [FINALLY BLOCK] BOOKING AGENT call - routing to Azure Blob Storage")

                session_transcript_manager = get_transcript_manager(session_id)
                success = await session_transcript_manager.extract_and_store_call_data(flow_manager)
                if success:
                    logger.success(f"✅ [FINALLY BLOCK] Booking agent call data saved to Azure for session: {session_id}")
                else:
                    logger.error(f"❌ [FINALLY BLOCK] Failed to save booking agent call data to Azure: {session_id}")

        except Exception as e:
            logger.error(f"❌ [FINALLY BLOCK] Error during call data extraction: {e}")
            import traceback
            traceback.print_exc()

        # Clear transcript session and cleanup
        cleanup_transcript_manager(session_id)

        # Cleanup sessions (COPIED FROM APP.PY)
        if session_id in active_sessions:
            del active_sessions[session_id]

        # STOP PER-CALL LOGGING (use session-specific logger)
        try:
            saved_log_file = session_call_logger.stop_call_logging()
            if saved_log_file:
                logger.info(f"📁 Call log saved: {saved_log_file}")
        except NameError:
            # Fallback: try to get logger from active_sessions
            try:
                if session_id in active_sessions and "call_logger" in active_sessions[session_id]:
                    saved_log_file = active_sessions[session_id]["call_logger"].stop_call_logging()
                    if saved_log_file:
                        logger.info(f"📁 Call log saved: {saved_log_file}")
            except Exception as fallback_error:
                logger.error(f"❌ Error in fallback call logging cleanup: {fallback_error}")
        except Exception as e:
            logger.error(f"❌ Error stopping call logging: {e}")

        logger.info(f"Healthcare Flow Session ended: {session_id}")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

if __name__ == "__main__":
    import uvicorn
    # EXACT SAME CONFIGURATION AS APP.PY
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("bot:app", host=host, port=port, reload=False)