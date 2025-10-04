"""
Pipeline components setup for TTS, STT, and LLM services
"""

from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from deepgram import LiveOptions
from loguru import logger

from config.settings import settings


def create_stt_service() -> DeepgramSTTService:
    """Create and configure Deepgram STT service"""
    config = settings.deepgram_config

    # ADD DEBUGGING LOGS
    logger.debug(f"🔍 Creating Deepgram STT with API key: {config['api_key'][:10]}...")
    logger.debug(f"🔍 Deepgram config: {config}")

    try:
        stt_service = DeepgramSTTService(
            api_key=config["api_key"],
            sample_rate=config["sample_rate"],
            live_options=LiveOptions(
                model=config["model"],
                language=config["language"],
                encoding=config["encoding"],
                channels=config["channels"],
                sample_rate=config["sample_rate"],
                interim_results=config["interim_results"],
                smart_format=config["smart_format"],
                punctuate=config["punctuate"],
                vad_events=config["vad_events"],
                profanity_filter=config["profanity_filter"],
                numerals=config["numerals"],
                keywords=config["keywords"]
            )
        )

        # ADD SUCCESS LOG
        logger.success("✅ Deepgram STT service created successfully")
        return stt_service

    except Exception as e:
        # ADD ERROR LOG
        logger.error(f"❌ Failed to create Deepgram STT service: {e}")
        raise


def create_tts_service() -> ElevenLabsTTSService:
    """Create and configure ElevenLabs TTS service"""
    config = settings.elevenlabs_config
    
    return ElevenLabsTTSService(
        api_key=config["api_key"],
        voice_id=config["voice_id"],
        model=config["model"],
        sample_rate=config["sample_rate"],
        stability=config["stability"],
        similarity_boost=config["similarity_boost"],
        style=config["style"],
        use_speaker_boost=config["use_speaker_boost"]
    )


def create_llm_service() -> OpenAILLMService:
    """Create and configure OpenAI LLM service"""
    config = settings.openai_config
    
    return OpenAILLMService(
        api_key=config["api_key"],
        model=config["model"]
    )


def create_context_aggregator(llm_service: OpenAILLMService) -> OpenAILLMContext:
    """Create context aggregator for the LLM"""
    return llm_service.create_context_aggregator(OpenAILLMContext([]))