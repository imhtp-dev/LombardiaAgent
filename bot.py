"""
Healthcare Flow Bot - Using Working app.py WebSocket Transport with bot.py Flows
EXACT COPY of app.py WebSocket implementation but with bot.py flow management
"""

import os
import re
import asyncio
import wave
import time
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv
from loguru import logger

# FastAPI (COPIED FROM APP.PY)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Core Pipecat imports (COPIED FROM APP.PY)
from pipecat.frames.frames import (
    TranscriptionFrame,
    InterimTranscriptionFrame,
    Frame,
    TTSSpeakFrame,
    LLMMessagesFrame,
    InputAudioRawFrame,
    OutputAudioRawFrame
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.openai.llm import OpenAILLMService

# EXACT SAME IMPORT AS APP.PY (this is what works with your bridge)
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

# VAD (COPIED FROM APP.PY)
from pipecat.audio.vad.silero import SileroVADAnalyzer, VADParams

# Serializer imports (COPIED FROM APP.PY)
from pipecat.serializers.base_serializer import FrameSerializer, FrameSerializerType

# Import flow management from bot.py
from flows.manager import create_flow_manager, initialize_flow_manager

# Import components from bot.py
from config.settings import settings
from services.config import config
from pipeline.components import create_stt_service, create_tts_service, create_llm_service, create_context_aggregator

load_dotenv(override=True)

# ================================================================================
# SIMPLE PCM SERIALIZER (COPIED FROM APP.PY)
# ================================================================================

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

# ================================================================================
# FASTAPI APP (COPIED FROM APP.PY)
# ================================================================================

app = FastAPI(
    title="Healthcare Flow Bot with Working WebSocket",
    description="Healthcare flow bot using app.py WebSocket transport",
    version="5.0.0"
)

# CORS configuration (COPIED FROM APP.PY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store for active sessions (COPIED FROM APP.PY)
active_sessions: Dict[str, Any] = {}

# ================================================================================
# HOMEPAGE (COPIED FROM APP.PY)
# ================================================================================

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

# ================================================================================
# MAIN WEBSOCKET ENDPOINT (USING APP.PY STRUCTURE WITH BOT.PY FLOWS)
# ================================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Healthcare Flow Bot WebSocket endpoint
    USES EXACT SAME STRUCTURE AS APP.PY BUT WITH BOT.PY FLOW INTELLIGENCE
    """
    await websocket.accept()

    # Extract parameters from query string (COPIED FROM APP.PY)
    query_params = dict(websocket.query_params)
    business_status = query_params.get("business_status", "open")
    session_id = query_params.get("session_id", f"session-{len(active_sessions)}")
    start_node = query_params.get("start_node", "greeting")

    logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"New Healthcare Flow WebSocket Connection")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Business Status: {business_status}")
    logger.info(f"Start Node: {start_node}")
    logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Variables for pipeline (COPIED FROM APP.PY)
    runner = None
    task = None

    try:
        # Check required API keys (COPIED FROM APP.PY)
        required_keys = [
            ("DEEPGRAM_API_KEY", "Deepgram"),
            ("ELEVENLABS_API_KEY", "ElevenLabs"),
            ("OPENAI_API_KEY", "OpenAI")
        ]

        for key_name, service_name in required_keys:
            if not os.getenv(key_name):
                raise Exception(f"{key_name} not found - required for {service_name}")

        # Validate health service configuration (FROM BOT.PY)
        try:
            config.validate()
            logger.success("✅ Health services configuration validated")
        except Exception as e:
            logger.error(f"❌ Health services configuration error: {e}")
            raise

        # CREATE TRANSPORT EXACTLY LIKE APP.PY
        transport = FastAPIWebsocketTransport(
            websocket=websocket,
            params=FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                add_wav_header=False,
                vad_analyzer=SileroVADAnalyzer(
                    params=VADParams(
                        start_secs=0.1,    # Reduced from 0.2 - detects speech faster
                        stop_secs=0.3,     # Reduced from 0.5 - stops listening sooner
                        min_volume=0.2     # Reduced from 0.4 - more sensitive to quiet speech
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

        logger.info("✅ All services initialized")

        # CREATE PIPELINE (SIMPLE LIKE APP.PY)
        pipeline = Pipeline([
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant()
        ])

        logger.info("Healthcare Flow Pipeline structure:")
        logger.info("  1. Input (PCM from bridge)")
        logger.info("  2. Deepgram STT")
        logger.info("  3. Context Aggregator (User)")
        logger.info("  4. OpenAI LLM (with flows)")
        logger.info("  5. ElevenLabs TTS")
        logger.info("  6. Output (PCM to bridge)")
        logger.info("  7. Context Aggregator (Assistant)")

        # Create pipeline task (COPIED FROM APP.PY)
        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_transcriptions=True,
                audio_in_sample_rate=16000,
                audio_out_sample_rate=16000,
            )
        )

        # CREATE FLOW MANAGER (FROM BOT.PY)
        flow_manager = create_flow_manager(task, llm, context_aggregator, transport)

        # Initialize STT switcher for dynamic transcription (FROM BOT.PY)
        from utils.stt_switcher import initialize_stt_switcher
        initialize_stt_switcher(stt, flow_manager)

        # ============================================
        # EVENT HANDLERS (COPIED FROM APP.PY STRUCTURE)
        # ============================================

        # Transport event handlers
        @transport.event_handler("on_client_connected")
        async def on_client_connected(transport_obj, ws):
            logger.info(f"✅ Healthcare Flow Client connected: {session_id}")
            active_sessions[session_id] = {
                "websocket": ws,
                "business_status": business_status,
                "connected_at": asyncio.get_event_loop().time(),
                "services": {
                    "stt": "deepgram",
                    "llm": "openai-gpt4-flows",
                    "tts": "elevenlabs",
                    "flows": "pipecat-flows"
                }
            }

            # Initialize flow manager (FROM BOT.PY)
            try:
                await initialize_flow_manager(flow_manager, start_node)
                logger.success(f"✅ Flow initialized with {start_node} node")
            except Exception as e:
                logger.error(f"Error during flow initialization: {e}")

        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(transport_obj, ws):
            logger.info(f"🔌 Healthcare Flow Client disconnected: {session_id}")

            # Cleanup (COPIED FROM APP.PY)
            if session_id in active_sessions:
                del active_sessions[session_id]

            await task.cancel()

        @transport.event_handler("on_session_timeout")
        async def on_session_timeout(transport_obj, ws):
            logger.warning(f"⏱️ Session timeout: {session_id}")

            # Cleanup (COPIED FROM APP.PY)
            if session_id in active_sessions:
                del active_sessions[session_id]

            await task.cancel()

        # ============================================
        # STT EVENT HANDLERS (COPIED FROM APP.PY)
        # ============================================

        @stt.event_handler("on_transcription")
        async def on_transcription(stt_service, transcription):
            """Handler for final transcribed text"""
            logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info(f"🎤 HEALTHCARE FLOW TRANSCRIPTION:")
            logger.info(f"   Text: '{transcription}'")
            logger.info(f"   Length: {len(transcription)} characters")
            logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        @stt.event_handler("on_interim_transcription")
        async def on_interim_transcription(stt_service, transcription):
            """Handler for interim transcriptions during speech"""
            logger.debug(f"📝 [INTERIM] Healthcare flow transcription: '{transcription}'")

        @stt.event_handler("on_error")
        async def on_stt_error(stt_service, error):
            """Handler for transcription errors"""
            logger.error(f"❌ DEEPGRAM STT ERROR: {error}")

        # ============================================
        # START PIPELINE (COPIED FROM APP.PY)
        # ============================================

        # Start pipeline
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
        # Cleanup sessions (COPIED FROM APP.PY)
        if session_id in active_sessions:
            del active_sessions[session_id]

        logger.info(f"Healthcare Flow Session ended: {session_id}")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

if __name__ == "__main__":
    import uvicorn
    # EXACT SAME CONFIGURATION AS APP.PY
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("bot:app", host=host, port=port, reload=False)