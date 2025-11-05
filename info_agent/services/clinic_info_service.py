"""
Clinic Information Service
Provides clinic hours, locations, summer closures, blood collection times via call_graph API
"""

import asyncio
import aiohttp
from typing import Optional
from dataclasses import dataclass
from loguru import logger

from info_agent.config.settings import info_settings


@dataclass
class ClinicInfoResult:
    """Result from clinic information query"""
    answer: str
    location: Optional[str] = None
    info_type: Optional[str] = None
    success: bool = True
    error: Optional[str] = None


class ClinicInfoService:
    """Service for getting clinic information"""
    
    def __init__(self):
        self.api_url = info_settings.api_endpoints["call_graph"]
        self.timeout = info_settings.api_timeout
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info(f"🏥 Clinic Info Service initialized: {self.api_url}")
    
    async def initialize(self):
        """Initialize HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            logger.debug("🏥 HTTP session created for clinic info service")
    
    async def get_clinic_info(
        self,
        location: str,
        info_type: str
    ) -> ClinicInfoResult:
        """
        Get clinic information using call_graph API
        
        Args:
            location: Clinic location/city (e.g., 'Novara', 'Biella', 'Milano')
            info_type: Type of information (e.g., 'summer closures', 'blood collection times', 'hours')
            
        Returns:
            ClinicInfoResult with answer
        """
        try:
            await self.initialize()
            
            # Construct query as: "info_type, location location"
            query = f"{info_type}, {location} location"
            
            logger.info(f"🏥 Getting clinic info: '{query}'")
            
            request_data = {
                "q": query
            }
            
            async with self.session.post(
                self.api_url,
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                answer = data.get("answer", "")
                
                logger.success(f"✅ Clinic info retrieved for {location}")
                logger.debug(f"🏥 Answer preview: {answer[:200]}...")
                
                return ClinicInfoResult(
                    answer=answer,
                    location=location,
                    info_type=info_type,
                    success=True
                )
                
        except aiohttp.ClientResponseError as e:
            logger.error(f"❌ Clinic info API error {e.status}: {e.message}")
            return ClinicInfoResult(
                answer="Mi dispiace, non riesco a recuperare le informazioni sulla clinica. Vuoi parlare con un operatore?",
                location=location,
                info_type=info_type,
                success=False,
                error=f"API error: {e.status}"
            )
        
        except asyncio.TimeoutError:
            logger.error(f"❌ Clinic info query timeout after {self.timeout}s")
            return ClinicInfoResult(
                answer="Mi dispiace, la ricerca sta richiedendo troppo tempo. Vuoi parlare con un operatore?",
                location=location,
                info_type=info_type,
                success=False,
                error="Timeout"
            )
        
        except Exception as e:
            logger.error(f"❌ Clinic info query failed: {e}")
            return ClinicInfoResult(
                answer="Mi dispiace, ho riscontrato un errore. Vuoi parlare con un operatore?",
                location=location,
                info_type=info_type,
                success=False,
                error=str(e)
            )
    
    async def cleanup(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            logger.debug("🏥 HTTP session closed for clinic info service")
            self.session = None


# Global instance
clinic_info_service = ClinicInfoService()