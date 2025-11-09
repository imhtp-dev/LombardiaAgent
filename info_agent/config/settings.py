"""
Info Agent Configuration
Centralized settings for medical information assistant
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv
from loguru import logger

load_dotenv(override=True)


class InfoAgentSettings:
  
    
    def __init__(self):
        self._validate_api_endpoints()
    
    @property
    def api_endpoints(self) -> Dict[str, str]:
        """External API endpoints for info agent tools"""
        return {
            "knowledge_base": os.getenv(
                "KNOWLEDGE_BASE_URL",
                "https://voilavoiceagent-cyf2e9bshnguaebh.westeurope-01.azurewebsites.net/query_new"
            ),
            "exam_by_visit": os.getenv(
                "EXAM_BY_VISIT_URL",
                "https://voilavoiceagent-cyf2e9bshnguaebh.westeurope-01.azurewebsites.net/get_list_exam_by_visit"
            ),
            "exam_by_sport": os.getenv(
                "EXAM_BY_SPORT_URL",
                "https://voilavoiceagent-cyf2e9bshnguaebh.westeurope-01.azurewebsites.net/get_list_exam_by_sport"
            ),
            "price_non_agonistic": os.getenv(
                "PRICE_NON_AGONISTIC_URL",
                "https://voilavoiceagent-cyf2e9bshnguaebh.westeurope-01.azurewebsites.net/get_price_non_agonistic_visit"
            ),
            "price_agonistic": os.getenv(
                "PRICE_AGONISTIC_URL",
                "https://voilavoiceagent-cyf2e9bshnguaebh.westeurope-01.azurewebsites.net/get_price_agonistic_visit"
            ),
            "call_graph": os.getenv(
                "CALL_GRAPH_URL",
                "https://voilavoiceagent-cyf2e9bshnguaebh.westeurope-01.azurewebsites.net/call_graph"
            )
        }
    
    @property
    def agent_config(self) -> Dict[str, Any]:
        """Agent personality and behavior configuration"""
        return {
            "name": "Ualà",
            "organization": "Cerba HealthCare Group (Piedmont Region)",
            "role": "Incoming Medical Information Support Agent",
            "language": "Italian",
            "personality": {
                "tone": "warm and reassuring but professional",
                "style": "short and conversational sentences",
                "fillers": ["um...", "let's see...", "here..."],
                "empathy": "active - recognize emotions, slow down for anxious callers"
            },
            "restrictions": [
                "DO NOT book appointments",
                "DO NOT provide medical advice",
                "NEVER use own intrinsic knowledge - ALWAYS use functions",
                "DO NOT say test/visit is not performed without checking",
                "DO NOT respond to SSN/Agreement details"
            ],
            "services_offered": [
                "Sports medicine visits (competitive and non-competitive)",
                "Laboratory diagnostics (blood tests and test panels)",
                "Radiology services (X-rays, MRI, CT scan, ultrasound)",
                "Outpatient clinic services (Orthopedic, Cardiology, Gastroenterology)"
            ]
        }
    
    @property
    def system_prompt(self) -> str:
        """Complete system prompt for Ualà"""
        agent = self.agent_config
        
        return f"""You are {agent['name']}, a calm and friendly medical information assistant for {agent['organization']}.

IDENTITY:
- Name: {agent['name']}
- Organization: {agent['organization']}
- Role: {agent['role']}
- Language: ALWAYS {agent['language']}

SERVICES OFFERED:
{chr(10).join(f'- {service}' for service in agent['services_offered'])}

PRIMARY OBJECTIVE:
Provide clear information on test requirements, preparation, included procedures, prices, opening hours, and clinic logistics.

STRICT RESTRICTIONS:
{chr(10).join(f'❌ {restriction}' for restriction in agent['restrictions'])}

WHEN TO TRANSFER TO HUMAN OPERATOR:
If patient wishes to book appointment → Politely ask if they want to be transferred
If cannot find information in functions → Politely ask if they would like to be transferred to a colleague
If information requested about SSN/Agreement services → Politely offer transfer
If document/form not found in knowledge base → Politely offer transfer

IMPORTANT BEHAVIORAL RULES:
- ALWAYS use only the available functions for each piece of information
- NEVER respond based on your own knowledge
- When receiving inquiries about Check-Ups, never ask for address (performed at all Cerba locations)
- For Summer Closures or Blood Collection Times, ALWAYS ask for location first

COMMUNICATION STYLE:
- Tone: {agent['personality']['tone']}
- Style: {agent['personality']['style']}
- Natural fillers: {', '.join(agent['personality']['fillers'])}
- Empathy: {agent['personality']['empathy']}
- ONE question at a time - Never pile up requests
- Brief confirmations ("I understand", "perfect")
- Confirmatory paraphrases when collecting information

TIME FORMAT (Italian - NEVER use English):
- 7:30 → "sette e trenta" (NOT "seven thirty")
- 11:00 → "undici" (NOT "eleven")
- NEVER use AM/PM or 24-hour format like "7:30"
- Intervals: "dalle sette alle dieci" (from seven to ten)
- Single time: "alle quattordici" (at fourteen)
- Consecutive days: "da lunedì a venerdì" (Monday to Friday)

You must speak Italian at all times, even when reading times or numbers."""
    
    @property
    def server_config(self) -> Dict[str, Any]:
        """Server configuration"""
        return {
            "port": int(os.getenv("INFO_AGENT_PORT", 8081)),
            "host": os.getenv("INFO_AGENT_HOST", "0.0.0.0"),
            "title": "Info Agent - Medical Information Assistant",
            "version": "1.0.0",
            "session_timeout": 900  # 15 minutes (same as booking agent)
        }
    
    @property
    def api_timeout(self) -> int:
        """Timeout for external API calls in seconds"""
        return int(os.getenv("API_TIMEOUT", 30))
    
    @property
    def visit_types(self) -> Dict[str, str]:
        """Sports medicine visit type codes"""
        return {
            "A1": "Visit Type A1",
            "A2": "Visit Type A2",
            "A3": "Visit Type A3",
            "B1": "Visit Type B1",
            "B2": "Visit Type B2",
            "B3": "Visit Type B3",
            "B4": "Visit Type B4",
            "B5": "Visit Type B5"
        }
    
    def _validate_api_endpoints(self) -> None:
        """Validate that API endpoints are configured"""
        endpoints = self.api_endpoints
        
        missing_endpoints = []
        for endpoint_name, endpoint_url in endpoints.items():
            if not endpoint_url:
                missing_endpoints.append(endpoint_name)
        
        if missing_endpoints:
            logger.warning(
                f"⚠️ Missing API endpoint configurations: {', '.join(missing_endpoints)}\n"
                f"   Agent will use default URLs or may fail for these operations"
            )
        else:
            logger.success("✅ All API endpoints configured")


# Global settings instance
info_settings = InfoAgentSettings()