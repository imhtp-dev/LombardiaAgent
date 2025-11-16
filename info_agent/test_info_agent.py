"""
Daily Transport Testing for Info Agent
======================================

This script creates a Daily room and connects the info agent
for local testing before deployment.

Usage:
    python -m info_agent.test                    # Start with greeting
    python -m info_agent.test --debug            # Enable debug logging

"""

import os
import sys
import asyncio
import argparse
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from loguru import logger

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Core Pipecat imports
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
from pipecat.audio.vad.silero import SileroVADAnalyzer, VADParams

# Daily transport imports
from pipecat.transports.daily.transport import DailyParams, DailyTransport

# Import info agent components
from info_agent.flows.manager import create_flow_manager, initialize_flow_manager
from info_agent.config.settings import info_settings

# Adjust path for Docker environment
sys.path.insert(0, '/app')

# Reuse components from booking agent
from pipeline.components import (
    create_stt_service,
    create_tts_service,
    create_llm_service,
    create_context_aggregator
)
from config.settings import settings

load_dotenv(override=True)


class DailyTestConfig:
    """Configuration for Daily testing"""
    
    def __init__(self):
        self.daily_api_key = os.getenv("DAILY_API_KEY")
        self.daily_api_url = os.getenv("DAILY_API_URL", "https://api.daily.co/v1")
        
        if not self.daily_api_key:
            raise Exception("DAILY_API_KEY environment variable is required for testing")
    
    @property
    def daily_room_config(self) -> Dict[str, Any]:
        """Daily room configuration optimized for testing"""
        return {
            "privacy": "private",
            "properties": {
                "max_participants": 2,
                "enable_chat": False,
                "enable_screenshare": False,
                "enable_recording": "local",
                "eject_at_room_exp": True,
                "exp": None,
            }
        }
    
    @property
    def daily_transport_params(self) -> Dict[str, Any]:
        """Daily transport parameters for testing"""
        return {
            "audio_in_enabled": True,
            "audio_out_enabled": True,
            "transcription_enabled": False,
            "audio_in_sample_rate": 16000,
            "audio_out_sample_rate": 16000,
            "camera_enabled": False,
            "mic_enabled": True,
            "dial_in_timeout": 30,
            "connection_timeout": 30,
            "vad_analyzer": SileroVADAnalyzer(
                params=VADParams(
                    start_secs=0.1,
                    stop_secs=0.3,
                    min_volume=0.2
                )
            )
        }


class DailyInfoAgentTester:
    """Daily transport tester for info agent"""
    
    def __init__(self, start_node: str = "greeting"):
        self.config = DailyTestConfig()
        self.start_node = start_node
        self.session_id = f"info-test-{asyncio.get_event_loop().time()}"
        self.room_url: Optional[str] = None
        self.token: Optional[str] = None
        
        # Runtime components
        self.transport: Optional[DailyTransport] = None
        self.task: Optional[PipelineTask] = None
        self.runner: Optional[PipelineRunner] = None
        self.flow_manager = None
        
        logger.info(f"🎯 Starting Info Agent Daily test session: {self.session_id}")
    
    async def create_daily_room(self) -> tuple[str, str]:
        """Create a new Daily room for testing"""
        logger.info("🏠 Creating Daily room for info agent testing...")
        
        import aiohttp
        import time
        
        room_config = {
            "privacy": "public",
            "properties": {
                "max_participants": 10,
                "enable_chat": True,
                "enable_screenshare": False,
                "enable_recording": "local",
                "eject_at_room_exp": True,
                "exp": int(time.time()) + 7200,
                "enable_knocking": False,
                "enable_prejoin_ui": False,
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.config.daily_api_key}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            # Create room
            async with session.post(
                f"{self.config.daily_api_url}/rooms",
                json=room_config,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to create Daily room: {response.status} - {error_text}")
                
                room_data = await response.json()
                room_url = room_data.get("url")
                
                if not room_url:
                    raise Exception(f"No room URL in response: {room_data}")
            
            logger.success(f"✅ Daily room created: {room_url}")
            
            # Generate token for bot
            token_config = {
                "properties": {
                    "room_name": room_data.get("name"),
                    "is_owner": True,
                    "user_name": "Ualà - Info Agent",
                    "enable_screenshare": False,
                    "start_audio_off": False,
                    "start_video_off": True
                }
            }
            
            async with session.post(
                f"{self.config.daily_api_url}/meeting-tokens",
                json=token_config,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Failed to create Daily token: {response.status} - {error_text}")
                
                token_data = await response.json()
                token = token_data.get("token")
                
                if not token:
                    raise Exception(f"No token in response: {token_data}")
            
            logger.success(f"🎟️ Daily token generated for info agent")
        
        return room_url, token
    
    async def setup_transport_and_pipeline(self, room_url: str, token: str):
        """Setup Daily transport and pipeline"""
        logger.info("🔧 Setting up Daily transport and pipeline...")
        
        # Create Daily transport
        self.transport = DailyTransport(
            room_url=room_url,
            token=token,
            bot_name="Ualà - Info Agent (Testing)",
            params=DailyParams(**self.config.daily_transport_params)
        )
        
        logger.info("✅ Daily transport created")
        
        # Create services
        logger.info("Initializing AI services...")
        stt = create_stt_service()
        tts = create_tts_service()
        llm = create_llm_service()
        context_aggregator = create_context_aggregator(llm)
        logger.success("✅ All AI services initialized")
        
        # Create pipeline
        pipeline = Pipeline([
            self.transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            self.transport.output(),
            context_aggregator.assistant()
        ])
        
        logger.info("Info Agent Pipeline structure:")
        logger.info("  1. Daily Input (WebRTC)")
        logger.info("  2. Deepgram STT (Italian)")
        logger.info("  3. Context Aggregator (User)")
        logger.info("  4. OpenAI LLM (with flows)")
        logger.info("  5. ElevenLabs TTS (Italian)")
        logger.info("  6. Daily Output (WebRTC)")
        logger.info("  7. Context Aggregator (Assistant)")
        
        # Create task
        self.task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                audio_in_sample_rate=16000,
                audio_out_sample_rate=16000,
            )
        )
        
        logger.success("✅ Pipeline and task created")
        
        # Return all components needed for flow manager
        return llm, context_aggregator
    
    async def setup_event_handlers(self):
        """Setup Daily transport event handlers"""
        logger.info("🔧 Setting up event handlers...")
        
        @self.transport.event_handler("on_participant_joined")
        async def on_participant_joined(transport, participant):
            logger.info(f"✅ Client connected: {self.session_id}")
            logger.info(f"👤 Participant joined: {participant.get('user_name', 'Unknown')}")
            
            # Initialize flow
            await initialize_flow_manager(self.flow_manager, self.start_node)
            logger.success(f"✅ Info Agent flow initialized with {self.start_node} node")
        
        @self.transport.event_handler("on_audio_track_started")
        async def on_audio_track_started(transport, participant_id):
            logger.info(f"🎤 Audio track started for participant: {participant_id}")
        
        @self.transport.event_handler("on_audio_track_stopped")
        async def on_audio_track_stopped(transport, participant_id):
            logger.info(f"🔇 Audio track stopped for participant: {participant_id}")
        
        @self.transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            logger.info(f"🔌 Client disconnected: {self.session_id}")
            logger.info(f"👋 Participant left: {participant.get('user_name', 'Unknown')} (Reason: {reason})")
            
            # Stop test session
            if self.task:
                await self.task.cancel()
                logger.info("🛑 Info Agent test session ended")
        
        @self.transport.event_handler("on_call_state_updated")
        async def on_call_state_updated(transport, state):
            logger.info(f"📞 Call state updated: {state}")
        
        @self.transport.event_handler("on_error")
        async def on_error(transport, error):
            logger.error(f"❌ Daily transport error: {error}")
        
        logger.success("✅ Event handlers configured")
    
    async def run_test_session(self, room_url: Optional[str] = None, token: Optional[str] = None):
        """Run the Daily test session"""
        try:
            # Create room if not provided
            if not room_url or not token:
                room_url, token = await self.create_daily_room()
            
            self.room_url = room_url
            self.token = token
            
            # Setup transport and pipeline
            llm, context_aggregator = await self.setup_transport_and_pipeline(room_url, token)
            
            # Create flow manager
            self.flow_manager = create_flow_manager(self.task, llm, context_aggregator, self.transport)
            self.flow_manager.state["session_id"] = self.session_id
            
            # Setup event handlers
            await self.setup_event_handlers()
            
            # Display connection info
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info("🚀 INFO AGENT DAILY TESTING SESSION")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info(f"🏠 Room URL: {room_url}")
            logger.info(f"🎯 Agent: {info_settings.agent_config['name']}")
            logger.info(f"🔧 Session ID: {self.session_id}")
            logger.info(f"🗣️ Language: {info_settings.agent_config['language']}")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info("🎯 TESTING INSTRUCTIONS:")
            logger.info("   1. Open the room URL above in your browser")
            logger.info("   2. Allow microphone access when prompted")
            logger.info("   3. Start speaking in Italian to test the info agent")
            logger.info("   4. The bot will join automatically when you connect")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info("💡 TEST EXAMPLES:")
            logger.info("   • 'Quanto costa una visita agonistica?'")
            logger.info("   • 'Avete chiusure estive?'")
            logger.info("   • 'Quali esami servono per il calcio?'")
            logger.info("   • 'Voglio prenotare un appuntamento'")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info("   Press Ctrl+C to stop the testing session")
            logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            # Start pipeline
            self.runner = PipelineRunner()
            logger.info("🚀 Starting Info Agent pipeline...")
            
            # Run pipeline (blocks until session ends)
            await self.runner.run(self.task)
            
        except KeyboardInterrupt:
            logger.info("⌨️ Test session interrupted by user")
        except Exception as e:
            logger.error(f"❌ Error in Daily test session: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Cleaning up Daily test session...")
        
        # Cancel task
        if self.task:
            try:
                await self.task.cancel()
            except:
                pass
        
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
        except:
            pass
        
        logger.success("✅ Daily test session cleanup completed")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Daily Transport Testing for Info Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m info_agent.test                    # Test info agent with voice
  python -m info_agent.test --debug            # Enable debug logging
        """
    )
    
    parser.add_argument(
        "--start-node",
        default="greeting",
        help="Starting flow node (default: greeting)"
    )
    
    parser.add_argument(
        "--room-url",
        help="Existing Daily room URL (optional)"
    )
    
    parser.add_argument(
        "--token",
        help="Daily room token (required if --room-url is provided)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    return parser.parse_args()


async def main():
    """Main function"""
    args = parse_arguments()
    
    # Configure logging level
    if args.debug:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    # Validate arguments
    if args.room_url and not args.token:
        logger.error("❌ --token is required when --room-url is provided")
        sys.exit(1)
    
    # Check required environment variables
    required_env_vars = [
        "DAILY_API_KEY",
        "DEEPGRAM_API_KEY",
        "ELEVENLABS_API_KEY",
        "OPENAI_API_KEY"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    logger.info("🎯 Starting Daily Info Agent Testing...")
    logger.info(f"📍 Agent: {info_settings.agent_config['name']}")
    logger.info(f"🗣️ Language: {info_settings.agent_config['language']}")
    
    # Create and run tester
    tester = DailyInfoAgentTester(start_node=args.start_node)
    await tester.run_test_session(
        room_url=args.room_url,
        token=args.token
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Info Agent test session ended by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
