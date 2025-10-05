import os
from typing import Dict, Any
from dotenv import load_dotenv
from loguru import logger

load_dotenv(override=True)

class Settings:
    """Centralized configuration management"""
    
    def __init__(self):
        self._validate_required_keys()
    
    @property
    def api_keys(self) -> Dict[str, str]:
        """Get all required API keys"""
        return {
            "deepgram": os.getenv("DEEPGRAM_API_KEY"),
            "elevenlabs": os.getenv("ELEVENLABS_API_KEY"),
            "openai": os.getenv("OPENAI_API_KEY")
        }
    
    @property
    def deepgram_config(self) -> Dict[str, Any]:
        """Deepgram STT configuration with Nova-3"""
        return {
            "api_key": self.api_keys["deepgram"],
            "sample_rate": 16000,
            "model": "nova-3-general",  # Upgraded to Nova-3 for 53.4% better accuracy
            "language": "it",
            "encoding": "linear16",
            "channels": 1,
            "interim_results": True,
            "smart_format": True,
            "punctuate": True,
            "vad_events": False,
            "profanity_filter": False,
            "numerals": True,
            # Nova-3 uses keyterms instead of keywords for better recognition
            "keyterms": [
                "maschio", "femmina"
            ]
        }
    
    @property
    def elevenlabs_config(self) -> Dict[str, Any]:
        """ElevenLabs TTS configuration"""
        return {
            "api_key": self.api_keys["elevenlabs"],
            "voice_id": "gfKKsLN1k0oYYN9n2dXX",
            "model": "eleven_multilingual_v2",
            "sample_rate": 16000,
            "stability": 0.6,
            "similarity_boost": 0.8,
            "style": 0.1,
            "use_speaker_boost": True
        }
    
    @property
    def openai_config(self) -> Dict[str, Any]:
        """OpenAI LLM configuration"""
        return {
            "api_key": self.api_keys["openai"],
            "model": "gpt-4.1-mini"
        }
    

    
    @property
    def vad_config(self) -> Dict[str, Any]:
        """Voice Activity Detection configuration optimized for Nova-3"""
        return {
            "start_secs": 0.2,
            "stop_secs": 0.5,
            "min_volume": 0.4
        }
    
    @property
    def pipeline_config(self) -> Dict[str, Any]:
        """Pipeline configuration"""
        return {
            "allow_interruptions": True,
            "enable_metrics": False,
            "enable_usage_metrics": False
        }

    @property
    def language_config(self) -> str:
        """Global language instruction for prompts"""
        return "You need to speak Italian"
    
    def _validate_required_keys(self) -> None:
        """Validate that all required API keys are present"""
        required_keys = [
            ("DEEPGRAM_API_KEY", "Deepgram"),
            ("ELEVENLABS_API_KEY", "ElevenLabs"), 
            ("OPENAI_API_KEY", "OpenAI")
        ]
        
        missing_keys = []
        for key_name, service_name in required_keys:
            if not os.getenv(key_name):
                missing_keys.append(f"{key_name} required for {service_name}")
        
        if missing_keys:
            raise Exception("Missing required environment variables:\n" + "\n".join(missing_keys))

# Global settings instance
settings = Settings()