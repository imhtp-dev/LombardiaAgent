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

load_dotenv(override=True)



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



app = FastAPI(
    title=info_settings.server_config["title"],
    description="Pipecat-based medical information agent for Cerba Healthcare + Dashboard APIs",
    version=info_settings.server_config["version"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import API routers
from info_agent.api.database import db
from info_agent.api import auth, users, qa, dashboard, chat

# Import Q&A AI services initialization
from info_agent.api.qa import initialize_ai_services


# Startup event - Initialize database and AI services
@app.on_event("startup")
async def startup():
    """Initialize database pool and AI services on startup"""
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
    
    logger.success("✅ Info Agent startup complete (voice agent ready)")


# Shutdown event - Cleanup database
@app.on_event("shutdown")
async def shutdown():
    """Close database pool on shutdown"""
    logger.info("🛑 Shutting down Info Agent + Dashboard APIs...")
    
    try:
        await db.close()
        logger.info("✅ Database connection pool closed")
    except Exception as e:
        logger.error(f"❌ Shutdown cleanup error: {e}")


# Include API routers
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
    
    # Extract session parameters
    query_params = dict(websocket.query_params)
    import uuid
    session_id = query_params.get("session_id", f"info-{uuid.uuid4().hex[:8]}")
    start_node = query_params.get("start_node", "greeting")
    caller_phone = query_params.get("caller_phone", "")
    
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("🎯 Info Agent - New Connection")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Start Node: {start_node}")
    logger.info(f"Caller Phone: {caller_phone or 'Not provided'}")
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
        
        # Create pipeline
        pipeline = Pipeline([
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant()
        ])
        
        logger.info("Info Agent Pipeline structure:")
        logger.info("  1. Input (PCM audio)")
        logger.info("  2. Deepgram STT (Italian)")
        logger.info("  3. Context Aggregator (User)")
        logger.info("  4. OpenAI LLM (with flows)")
        logger.info("  5. ElevenLabs TTS (Italian)")
        logger.info("  6. Output (PCM audio)")
        logger.info("  7. Context Aggregator (Assistant)")
        
        # Create pipeline task
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                audio_in_sample_rate=16000,
                audio_out_sample_rate=16000,
            )
        )
        
        logger.info("✅ Pipeline task created")
        
        # Create flow manager
        flow_manager = create_flow_manager(task, llm, context_aggregator, transport)
        
        # Store caller phone in flow state if provided
        if caller_phone:
            flow_manager.state["caller_phone"] = caller_phone
            logger.info(f"📞 Caller phone stored: {caller_phone}")
        
        # Store session ID
        flow_manager.state["session_id"] = session_id
        
        # Initialize call data extractor
        call_extractor = get_call_extractor(session_id)
        interaction_id = query_params.get("interaction_id")
        call_extractor.start_call(caller_phone=caller_phone, interaction_id=interaction_id)
        
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
            
            # End call timing
            call_extractor.end_call()
            
            # Extract transcript from context aggregator
            try:
                messages = context_aggregator.get_messages()
                for msg in messages:
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role and content:
                        call_extractor.add_transcript_entry(role, content)
            except Exception as e:
                logger.warning(f"⚠️ Could not extract transcript: {e}")
            
            # Save call data to database
            try:
                success = await call_extractor.save_to_database(flow_manager.state)
                if success:
                    logger.success("✅ Call data saved to Supabase")
                else:
                    logger.warning("⚠️ Call data extraction failed (check logs)")
            except Exception as e:
                logger.error(f"❌ Error saving call data: {e}")
            
            # Cleanup call extractor
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
