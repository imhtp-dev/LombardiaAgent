"""
Knowledge Base Service
Queries Cerba Healthcare knowledge base for medical information, FAQs, and documents
"""

import json
import asyncio
import aiohttp
from typing import Optional
from dataclasses import dataclass
from loguru import logger

from info_agent.config.settings import info_settings


@dataclass
class KnowledgeBaseResult:
    """Result from knowledge base query"""
    answer: str
    confidence: float
    source: Optional[str] = None
    success: bool = True
    error: Optional[str] = None


class KnowledgeBaseService:
    """Service for querying Cerba Healthcare knowledge base"""
    
    def __init__(self):
        self.api_url = info_settings.api_endpoints["knowledge_base"]
        self.timeout = info_settings.api_timeout
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info(f"📚 Knowledge Base Service initialized: {self.api_url}")
    
    async def initialize(self):
        """Initialize HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            logger.debug("📚 HTTP session created for knowledge base")
    
    async def query(self, question: str) -> KnowledgeBaseResult:
        """
        Query knowledge base with natural language question
        
        Args:
            question: Natural language question in Italian
            
        Returns:
            KnowledgeBaseResult with answer and confidence
        """
        try:
            await self.initialize()
            
            logger.info(f"📚 Querying knowledge base: '{question[:100]}...'")

            # VAPI-compatible request format
            request_data = {
                "message": {
                    "toolCallList": [
                        {
                            "toolCallId": "pipecat_knowledge_base",
                            "function": {
                                "name": "query_new",
                                "arguments": json.dumps({"query": question})
                            }
                        }
                    ]
                }
            }

            async with self.session.post(
                self.api_url,
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                response.raise_for_status()
                data = await response.json()

                # Debug: Log full API response
                logger.debug(f"🔍 API Response: {data}")

                # API returns {'results': [{'toolCallId': '...', 'result': {...}}]}
                results = data.get("results", [])

                if not results or len(results) == 0:
                    logger.warning("⚠️ API returned empty results")
                    return KnowledgeBaseResult(
                        answer="",
                        confidence=0.0,
                        success=False,
                        error="No results found"
                    )

                # Extract the knowledge base data from results[0]["result"]
                # Note: result is a dict object (not JSON string)
                kb_data = results[0].get("result", {})

                if not kb_data:
                    logger.warning("⚠️ API returned empty knowledge base data")
                    return KnowledgeBaseResult(
                        answer="",
                        confidence=0.0,
                        success=False,
                        error="Empty knowledge base data"
                    )

                answer = kb_data.get("answer", "")
                confidence = kb_data.get("confidence", 0.0)
                source = kb_data.get("source")

                logger.success(f"✅ Knowledge base returned answer (confidence: {confidence:.2f})")
                logger.debug(f"📚 Answer preview: {answer[:200]}...")

                return KnowledgeBaseResult(
                    answer=answer,
                    confidence=confidence,
                    source=source,
                    success=True
                )
                
        except aiohttp.ClientResponseError as e:
            logger.error(f"❌ Knowledge base API error {e.status}: {e.message}")
            return KnowledgeBaseResult(
                answer="Mi dispiace, non riesco ad accedere alle informazioni in questo momento. Vuoi parlare con un operatore?",
                confidence=0.0,
                success=False,
                error=f"API error: {e.status}"
            )
        
        except asyncio.TimeoutError:
            logger.error(f"❌ Knowledge base query timeout after {self.timeout}s")
            return KnowledgeBaseResult(
                answer="Mi dispiace, la ricerca sta richiedendo troppo tempo. Vuoi parlare con un operatore?",
                confidence=0.0,
                success=False,
                error="Timeout"
            )
        
        except Exception as e:
            logger.error(f"❌ Knowledge base query failed: {e}")
            return KnowledgeBaseResult(
                answer="Mi dispiace, ho riscontrato un errore. Vuoi parlare con un operatore?",
                confidence=0.0,
                success=False,
                error=str(e)
            )
    
    async def cleanup(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            logger.debug("📚 HTTP session closed for knowledge base")
            self.session = None


# Global instance
knowledge_base_service = KnowledgeBaseService()