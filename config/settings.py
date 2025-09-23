"""
Configuration settings for Healthcare Flow Bot
"""

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
            "openai": os.getenv("OPENAI_API_KEY"),
            "daily": os.getenv("DAILY_API_KEY")
        }
    
    @property
    def deepgram_config(self) -> Dict[str, Any]:
        """Deepgram STT configuration"""
        return {
            "api_key": self.api_keys["deepgram"],
            "sample_rate": 16000,
            "model": "nova-2-general",
            "language": "it",
            "encoding": "linear16",
            "channels": 1,
            "interim_results": True,
            "smart_format": True,
            "punctuate": True,
            "vad_events": False,
            "profanity_filter": False,
            "numerals": True
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
    def daily_config(self) -> Dict[str, Any]:
        """Daily transport configuration"""
        return {
            "api_key": self.api_keys["daily"],
            "room_properties": {
                "enable_prejoin_ui": False,
                "enable_screenshare": False,
                "enable_chat": False,
                "start_video_off": True,
                "start_audio_off": False
            },
            "params": {
                "audio_in_enabled": True,
                "audio_out_enabled": True,
                "transcription_enabled": False,
                "audio_in_sample_rate": 16000,
                "audio_out_sample_rate": 16000,
                "camera_enabled": False,
                "mic_enabled": True,
                "dial_in_timeout": 15.0,
                "connection_timeout": 10.0
            }
        }
    
    @property
    def vad_config(self) -> Dict[str, Any]:
        """Voice Activity Detection configuration"""
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
    
    def _validate_required_keys(self) -> None:
        """Validate that all required API keys are present"""
        required_keys = [
            ("DEEPGRAM_API_KEY", "Deepgram"),
            ("ELEVENLABS_API_KEY", "ElevenLabs"), 
            ("OPENAI_API_KEY", "OpenAI"),
            ("DAILY_API_KEY", "Daily")
        ]
        
        missing_keys = []
        for key_name, service_name in required_keys:
            if not os.getenv(key_name):
                missing_keys.append(f"{key_name} required for {service_name}")
        
        if missing_keys:
            raise Exception("Missing required environment variables:\n" + "\n".join(missing_keys))

# Global settings instance
settings = Settings()