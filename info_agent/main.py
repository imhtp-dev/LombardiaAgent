"""
Info Agent - Medical Information Assistant
Pipecat-based voice agent for Cerba Healthcare
Provides information without booking appointments
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from loguru import logger

# Add parent directory to path to import from booking agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


logging.getLogger("deepgram").setLevel(logging.DEBUG)
logging.getLogger("websockets").setLevel(logging.DEBUG)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware


from pipecat.frames.frames import (
    Frame,
    InputAudioRawFrame,
    OutputAudioRawFrame
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.audio.vad.silero import SileroVADAnalyzer, VADParams
from pipecat.serializers.base_serializer import FrameSerializer, FrameSerializerType
from pipecat.processors.transcript_processor import TranscriptProcessor  # ✅ NEW


from info_agent.flows.manager import create_flow_manager, initialize_flow_manager
from info_agent.services.call_data_extractor import get_call_extractor, cleanup_call_extractor

from info_agent.config.settings import info_settings


from pipeline.components import (
    create_stt_service,
    create_tts_service,
    create_llm_service,
    create_context_aggregator
)
from config.settings import settings as booking_settings



class RawPCMSerializer(FrameSerializer):
    """Simple serializer for PCM audio (16kHz, mono)"""

    @property
    def type(self):
        return FrameSerializerType.BINARY

    async def serialize(self, frame: Frame) -> bytes:
        """Serialize outgoing audio frames"""
        if isinstance(frame, OutputAudioRawFrame):
            return frame.audio
        return b''

    async def deserialize(self, data) -> Frame:
        """Deserialize incoming PCM audio"""
        if isinstance(data, bytes) and len(data) > 0:
            return InputAudioRawFrame(
                audio=data,
                sample_rate=16000,
                num_channels=1
            )
        return None


# Import dependencies before app creation
from info_agent.api.database import db
from info_agent.api import auth, users, qa, dashboard, chat
from info_agent.api.qa import initialize_ai_services
from info_agent.services.call_retry_service import start_retry_service, stop_retry_service


# Lifespan context manager - Modern FastAPI approach (replaces @app.on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown operations.
    This replaces the deprecated @app.on_event decorators.
    """
    # Startup operations
    logger.info("🚀 Starting Info Agent + Dashboard APIs...")

    # Try to initialize database (optional for voice agent)
    try:
        await db.connect()
        logger.info("✅ Database connection pool initialized")
    except Exception as e:
        logger.warning(f"⚠️ Database connection failed (dashboard APIs will not work): {e}")
        logger.info("✅ Voice agent will still function normally")

    # Try to initialize Pinecone and OpenAI for Q&A management (optional)
    try:
        initialize_ai_services()
        logger.info("✅ AI services (Pinecone + OpenAI) initialized")
    except Exception as e:
        logger.warning(f"⚠️ AI services initialization failed (Q&A management APIs will not work): {e}")
        logger.info("✅ Voice agent will still function normally")

    # Start call retry service for failed database saves
    try:
        await start_retry_service()
        logger.info("✅ Call Retry Service started (checks every 5 minutes)")
    except Exception as e:
        logger.warning(f"⚠️ Call Retry Service failed to start: {e}")
        logger.info("✅ Voice agent will still function (manual retry needed for failures)")

    logger.success("✅ Info Agent startup complete (voice agent ready)")

    # Yield control to the application (runs during app lifetime)
    yield

    # Shutdown operations
    logger.info("🛑 Shutting down Info Agent + Dashboard APIs...")

    # Stop call retry service
    try:
        await stop_retry_service()
        logger.info("✅ Call Retry Service stopped")
    except Exception as e:
        logger.error(f"❌ Retry service shutdown error: {e}")

    try:
        await db.close()
        logger.info("✅ Database connection pool closed")
    except Exception as e:
        logger.error(f"❌ Shutdown cleanup error: {e}")


# Create FastAPI app with lifespan
app = FastAPI(
    title=info_settings.server_config["title"],
    description="Pipecat-based medical information agent for Cerba Healthcare + Dashboard APIs",
    version=info_settings.server_config["version"],
    lifespan=lifespan  # ✅ Modern approach - replaces @app.on_event
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(qa.router, prefix="/api/qa", tags=["Q&A Management"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])

logger.info("✅ API routers registered:")
logger.info("   - /api/auth/* (Authentication)")
logger.info("   - /api/users/* (User Management)")
logger.info("   - /api/qa/* (Q&A Management)")
logger.info("   - /api/dashboard/* (Dashboard Statistics)")
logger.info("   - /api/chat/* (Chat Interface)")


active_sessions: Dict[str, Any] = {}


@app.get("/")
async def root():
    """Homepage with agent information"""
    return HTMLResponse(f"""
    <html>
        <head>
            <title>Info Agent - Ualà</title>
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
                <h1>🏥 Info Agent - Ualà</h1>
                <p class="status">✅ Medical Information Assistant is running</p>

                <h2>Agent Details:</h2>
                <ul>
                    <li><strong>Name:</strong> {info_settings.agent_config['name']}</li>
                    <li><strong>Organization:</strong> {info_settings.agent_config['organization']}</li>
                    <li><strong>Role:</strong> {info_settings.agent_config['role']}</li>
                    <li><strong>Language:</strong> {info_settings.agent_config['language']}</li>
                </ul>

                <h2>Active Services:</h2>
                <div>
                    <span class="service">Deepgram STT (Italian)</span>
                    <span class="service">OpenAI GPT-4.1-mini</span>
                    <span class="service">ElevenLabs TTS (Italian)</span>
                    <span class="service">Pipecat Flows</span>
                </div>

                <h2>Endpoints:</h2>
                <ul>
                    <li><code>GET /</code> - This page</li>
                    <li><code>GET /health</code> - Health check</li>
                    <li><code>WS /ws</code> - WebSocket endpoint</li>
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
        "service": "info-agent",
        "agent": info_settings.agent_config["name"],
        "version": info_settings.server_config["version"],
        "active_sessions": len(active_sessions),
        "services": {
            "stt": "deepgram",
            "llm": "openai-gpt4.1-mini",
            "tts": "elevenlabs",
            "flows": "pipecat-flows"
        }
    })


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for info agent
    Handles medical information queries via voice
    """
    await websocket.accept()

    # ✅ Ensure database pool is initialized (for direct WebSocket connections)
    logger.debug(f"🔍 Checking database pool status: pool={'initialized' if db.pool else 'None'}")
    if not db.pool:
        logger.warning("⚠️ Database pool not initialized, initializing now...")
        try:
            await db.connect()
            if db.pool:
                logger.success("✅ Database connection pool initialized")
            else:
                logger.warning("⚠️ Database connection failed (pool is still None)")
        except Exception as e:
            logger.warning(f"⚠️ Database connection failed: {e}")
            logger.info("✅ Voice agent will continue (backup files will be created)")
    else:
        logger.debug("✅ Database pool already initialized")

    # ✅ Extract ALL session parameters (from TalkDesk bridge)
    query_params = dict(websocket.query_params)
    import uuid
    session_id = query_params.get("session_id", f"info-{uuid.uuid4().hex[:8]}")
    start_node = query_params.get("start_node", "greeting")
    caller_phone = query_params.get("caller_phone", "")
    interaction_id = query_params.get("interaction_id", "")  # ✅ NEW
    stream_sid = query_params.get("stream_sid", "")          # ✅ NEW
    business_status = query_params.get("business_status", "open")  # ✅ NEW

    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("🎯 Info Agent - New Connection")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Start Node: {start_node}")
    logger.info(f"Caller Phone: {caller_phone or 'Not provided'}")
    logger.info(f"Interaction ID: {interaction_id or 'Not provided'}")  # ✅ NEW
    logger.info(f"Stream SID: {stream_sid or 'Not provided'}")          # ✅ NEW
    logger.info(f"Business Status: {business_status}")                  # ✅ NEW
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    runner = None
    task = None

    try:
        # Validate API keys
        required_keys = [
            ("DEEPGRAM_API_KEY", "Deepgram"),
            ("ELEVENLABS_API_KEY", "ElevenLabs"),
            ("OPENAI_API_KEY", "OpenAI")
        ]
        
        for key_name, service_name in required_keys:
            if not os.getenv(key_name):
                raise Exception(f"{key_name} not found - required for {service_name}")
        
        logger.success("✅ All API keys validated")
        
        # Create transport
        transport = FastAPIWebsocketTransport(
            websocket=websocket,
            params=FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                add_wav_header=False,
                vad_analyzer=SileroVADAnalyzer(
                    params=VADParams(
                        start_secs=booking_settings.vad_config["start_secs"],
                        stop_secs=booking_settings.vad_config["stop_secs"],
                        min_volume=booking_settings.vad_config["min_volume"]
                    )
                ),
                serializer=RawPCMSerializer(),
                session_timeout=info_settings.server_config["session_timeout"],
            )
        )
        
        logger.info("✅ Transport created")
        
        # Create services (reuse from booking agent)
        logger.info("Initializing AI services...")
        stt = create_stt_service()
        tts = create_tts_service()
        llm = create_llm_service()
        context_aggregator = create_context_aggregator(llm)
        logger.success("✅ All AI services initialized")

        # ✅ Create TranscriptProcessor for real-time transcript capture
        transcript_processor = TranscriptProcessor()
        logger.info("✅ TranscriptProcessor created")

        # Initialize call data extractor BEFORE pipeline
        call_extractor = get_call_extractor(session_id)
        call_extractor.start_call(
            caller_phone=caller_phone,
            interaction_id=interaction_id
        )
        # Store call_id from session_id (bridge UUID)
        call_extractor.call_id = session_id

        # ✅ Setup transcript event handler
        @transcript_processor.event_handler("on_transcript_update")
        async def on_transcript_update(processor, frame):
            """Capture transcript in real-time"""
            for message in frame.messages:
                logger.debug(f"📝 {message.role}: {message.content[:50]}...")
                call_extractor.add_transcript_entry(message.role, message.content)

        # ✅ Create pipeline WITH TranscriptProcessor
        pipeline = Pipeline([
            transport.input(),
            stt,
            transcript_processor.user(),        # ✅ NEW - Capture user messages
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            transcript_processor.assistant(),   # ✅ NEW - Capture assistant messages
            context_aggregator.assistant()
        ])

        logger.info("Info Agent Pipeline structure:")
        logger.info("  1. Input (PCM audio)")
        logger.info("  2. Deepgram STT (Italian)")
        logger.info("  3. TranscriptProcessor.user() - Capture user messages")  # ✅ NEW
        logger.info("  4. Context Aggregator (User)")
        logger.info("  5. OpenAI LLM (with flows)")
        logger.info("  6. ElevenLabs TTS (Italian)")
        logger.info("  7. Output (PCM audio)")
        logger.info("  8. TranscriptProcessor.assistant() - Capture assistant messages")  # ✅ NEW
        logger.info("  9. Context Aggregator (Assistant)")

        # ✅ Create pipeline task WITH METRICS ENABLED
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                audio_in_sample_rate=16000,
                audio_out_sample_rate=16000,
                enable_metrics=True,           # ✅ NEW - Enable metrics
                enable_usage_metrics=True      # ✅ NEW - Track tokens
            )
        )
        
        logger.info("✅ Pipeline task created")
        
        # Create flow manager
        flow_manager = create_flow_manager(task, llm, context_aggregator, transport)

        # ✅ Store ALL parameters in flow state
        flow_manager.state.update({
            "session_id": session_id,
            "caller_phone": caller_phone,
            "interaction_id": interaction_id,
            "stream_sid": stream_sid,
            "business_status": business_status
        })

        logger.info(f"📞 Caller phone stored: {caller_phone or 'N/A'}")
        logger.info(f"📋 Interaction ID stored: {interaction_id or 'N/A'}")
        logger.info(f"📡 Stream SID stored: {stream_sid or 'N/A'}")
        
        # Event handlers
        @transport.event_handler("on_client_connected")
        async def on_client_connected(transport_obj, ws):
            logger.info(f"✅ Client connected: {session_id}")
            
            # Store session info
            active_sessions[session_id] = {
                "websocket": ws,
                "connected_at": asyncio.get_event_loop().time(),
                "agent": "info",
                "flow_manager": flow_manager,
                "call_extractor": call_extractor,
                "services": {
                    "stt": "deepgram",
                    "llm": "openai-gpt4.1-mini",
                    "tts": "elevenlabs",
                    "flows": "pipecat-flows"
                }
            }
            
            # Initialize flow
            try:
                await initialize_flow_manager(flow_manager, start_node)
                logger.success(f"✅ Flow initialized with {start_node} node")
            except Exception as e:
                logger.error(f"❌ Flow initialization error: {e}")
        
        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport_obj, ws):
            logger.info(f"🔌 Client disconnected: {session_id}")

            # ✅ End call timing
            call_extractor.end_call()

            # ✅ Transcript is already captured by TranscriptProcessor (no need to extract from context_aggregator)
            logger.info(f"📝 Transcript captured: {len(call_extractor.transcript)} messages")

            # ✅ Populate flow state with functions called
            flow_manager.state["functions_called"] = [
                f["function_name"] for f in call_extractor.functions_called
            ]

            # ✅ Save call data to database (UPDATE existing row)
            try:
                logger.info(f"📊 Saving call data to database...")
                # ✅ CRITICAL: Mark call end time before saving
                call_extractor.end_call()
                success = await call_extractor.save_to_database(flow_manager.state)
                if success:
                    logger.success("✅ Call data saved to Supabase tb_stat")
                    logger.info(f"   Call ID: {call_extractor.call_id}")
                    logger.info(f"   Duration: {call_extractor._calculate_duration()}s")
                    logger.info(f"   Transcript: {len(call_extractor.transcript)} messages")
                    logger.info(f"   Functions: {len(call_extractor.functions_called)} calls")
                else:
                    logger.warning("⚠️ Call data save failed (saved to backup file)")
            except Exception as e:
                logger.error(f"❌ Error saving call data: {e}")
                import traceback
                traceback.print_exc()

            # ✅ Cleanup call extractor
            cleanup_call_extractor(session_id)

            # Check if transfer was requested
            if flow_manager.state.get("transfer_requested"):
                transfer_reason = flow_manager.state.get("transfer_reason", "unknown")
                logger.info(f"📞 Transfer was requested: {transfer_reason}")
                # TODO: Call escalation endpoint here (future integration)

            # Cleanup
            if session_id in active_sessions:
                del active_sessions[session_id]

            await task.cancel()
        
        @transport.event_handler("on_session_timeout")
        async def on_session_timeout(transport_obj, ws):
            logger.warning(f"⏱️ Session timeout: {session_id}")
            
            # Cleanup
            if session_id in active_sessions:
                del active_sessions[session_id]
            
            await task.cancel()
        
        # Run pipeline
        runner = PipelineRunner()
        
        logger.info(f"🚀 Info Agent pipeline started for session: {session_id}")
        logger.info(f"🏥 Medical information flows ACTIVE")
        
        # Run pipeline (blocks until disconnection)
        await runner.run(task)
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"❌ Error in Info Agent WebSocket handler: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup sessions
        if session_id in active_sessions:
            del active_sessions[session_id]
        
        # Cleanup services
        try:
            from info_agent.services.knowledge_base import knowledge_base_service
            from info_agent.services.pricing_service import pricing_service
            from info_agent.services.exam_service import exam_service
            from info_agent.services.clinic_info_service import clinic_info_service
            
            await knowledge_base_service.cleanup()
            await pricing_service.cleanup()
            await exam_service.cleanup()
            await clinic_info_service.cleanup()
            logger.debug("✅ Services cleaned up")
        except Exception as cleanup_error:
            logger.error(f"❌ Cleanup error: {cleanup_error}")
        
        logger.info(f"Session ended: {session_id}")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    import uvicorn
    
    port = info_settings.server_config["port"]
    host = info_settings.server_config["host"]
    
    logger.info(f"🚀 Starting Info Agent on {host}:{port}")
    logger.info(f"🏥 Agent: {info_settings.agent_config['name']}")
    logger.info(f"🗣️ Language: {info_settings.agent_config['language']}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False
    )
