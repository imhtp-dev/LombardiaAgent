"""
Pipeline components setup for TTS, STT, and LLM services
"""

from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from deepgram import LiveOptions
from loguru import logger
from typing import Union

try:
    from pipecat.services.azure.stt import AzureSTTService
    from pipecat.transcriptions.language import Language
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    Language = None
    logger.warning("Azure STT not available. Install with: pip install 'pipecat-ai[azure]'")

from config.settings import settings


def create_stt_service() -> Union[DeepgramSTTService, "AzureSTTService"]:
    """Create and configure STT service based on provider setting"""
    provider = settings.stt_provider

    logger.info(f"🎙️ Creating {provider.upper()} STT service")

    if provider == "azure":
        return create_azure_stt_service()
    else:
        return create_deepgram_stt_service()


def create_deepgram_stt_service() -> DeepgramSTTService:
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
                numerals=config["numerals"]
            )
        )

        # ADD SUCCESS LOG
        logger.success("✅ Deepgram STT service created successfully")
        return stt_service

    except Exception as e:
        # ADD ERROR LOG
        logger.error(f"❌ Failed to create Deepgram STT service: {e}")
        raise


def create_azure_stt_service() -> "AzureSTTService":
    """Create and configure Azure STT service"""
    if not AZURE_AVAILABLE:
        logger.error("❌ Azure STT not available. Install with: pip install 'pipecat-ai[azure]'")
        raise ImportError("Azure STT service not available")

    config = settings.azure_stt_config

    # ADD DEBUGGING LOGS
    logger.debug(f"🔍 Creating Azure STT with region: {config['region']}")
    logger.debug(f"🔍 Azure STT config: {config}")

    try:
        # Prepare service parameters
        service_params = {
            "api_key": config["api_key"],
            "region": config["region"],
            "sample_rate": config["sample_rate"]
        }

        # Add language if available (convert string to Language enum if needed)
        language_code = config.get("language", "it-IT")
        if Language:
            # Map language codes to Language enum values
            language_map = {
                "it-IT": Language.IT_IT,
                "en-US": Language.EN_US,
                "es-ES": Language.ES_ES,
                "fr-FR": Language.FR_FR,
                "de-DE": Language.DE_DE
            }
            service_params["language"] = language_map.get(language_code, Language.IT_IT)

        # Add optional endpoint_id if provided
        if config.get("endpoint_id"):
            service_params["endpoint_id"] = config["endpoint_id"]

        stt_service = AzureSTTService(**service_params)

        # ADD SUCCESS LOG
        logger.success("✅ Azure STT service created successfully")
        return stt_service

    except Exception as e:
        # ADD ERROR LOG
        logger.error(f"❌ Failed to create Azure STT service: {e}")
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