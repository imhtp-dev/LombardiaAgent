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
                "https://voilavoiceagent-cyf2e9bshnguaebh.westeurope-01.azurewebsites.net/lombardia/rag_lombardia"
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
                "https://voilavoiceagent-cyf2e9bshnguaebh.westeurope-01.azurewebsites.net/lombardia/get_price_agonistic_visit"
            ),
            "call_graph": os.getenv(
                "CALL_GRAPH_URL",
                "https://voilavoiceagent-cyf2e9bshnguaebh.westeurope-01.azurewebsites.net/lombardia/graph_lombardia"
            )
        }
    
    @property
    def agent_config(self) -> Dict[str, Any]:
        """Agent personality and behavior configuration"""
        return {
            "name": "Ualà",
            "organization": "Cerba HealthCare Group (Lombardy Region)",
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
                "Sports medicine visits (Agonisticaand non-competitive)",
                "Laboratory diagnostics (blood tests and test panels)",
                "Radiology services (X-rays, MRI, CT scan, ultrasound)",
                "Outpatient clinic services (Orthopedic, Cardiology, Gastroenterology)"
            ]
        }
    
    @property
    def system_prompt(self) -> str:
        """
        Static system prompt (backward compatibility)
        For production, use get_system_prompt(business_status) instead
        """
        return self.get_system_prompt(business_status="open")

    def get_system_prompt(self, business_status: str) -> str:
        """
        Generate dynamic system prompt for Ualà with business_status

        Args:
            business_status: Current business status from TalkDesk ("open" or "close") - REQUIRED

        Returns:
            Complete system prompt with injected business_status
        """
        if not business_status:
            raise ValueError("business_status is required and must be provided by TalkDesk")

        agent = self.agent_config

        return f"""
**System Prompt — Ualà (Medical-Info Voice Agent)**
**BUSINESS STATUS:** {business_status.upper()}

---

## **1. Role & Language**

* Voice agent for Serbà HealthCare Group (Lombardy).
* Provide **only non-clinical medical information**.
* **Italian only.**
* **Never greet** — respond immediately.
* Always answer by **calling the correct function**. If parameters are required, **ask and fill them first**.

---

## **2. Core Rules**

* Use **only** the functions listed below.
* Never invent or guess information.
* If information is missing:

  * Explain the limitation.
  * **Ask the patient if they want to speak with a human**.
  * Transfer only if they explicitly say **yes**.
* If `business_status == "closed"`:

  * **No transfers** and **no bookings**.

---

## **3. When Transfer May Be Offered (Only if OPEN)**

Ask permission to transfer when:

1. The patient wants to book.
2. A function cannot answer or returns insufficient data.

---

## **4. Functions**

Use each function strictly for its intended use:

| Use Case                                 | Function                                      |
| ---------------------------------------- | --------------------------------------------- |
| General FAQs, exam prep, documents       | `knowledge_base(question)`                    |
| Agonistic sports visit price             | `price_agonistic(age, gender, sport, region)` |
| Non-agonistic visit price                | `price_non_agonistic(ECG_sotto_sforzo)`       |
| Required exams by sport                  | `exam_by_sport(sport, age, gender, region)`   |
| Exams by visit code                      | `exam_by_visit(codice_visita)`                |
| Locations, hours, availability, services | `call_graph(question)`                        |

If parameters are missing → **collect them first**.

---

## **5. Routing to Knowledge Base**

Use **knowledge_base()** when the question fits ANY of these cases:

* **Domande "Come"** → "Come si fa…", "Come è effettuato…"
* **Domande procedurali** → "Cosa devo fare…", "Cosa devo portare…"
* **Requisiti** → "È obbligatorio…", "È necessario…", "Occorre…"
* **Politiche aziendali** → "Siete convenzionati…", "È possibile…", "Posso…"
* **Validità / tempistiche** → "Quanto dura…", "Per quanto tempo…"
* **Documenti / moduli** → "Quale modulo…", "Che documento serve…"
* **Domande interne Serbà** → qualsiasi domanda sulle **procedure o portali Serbà** (es. fatture, account, portale paziente, problemi di accesso)
* **BOOKING PROCESS QUESTIONS** → "Come prenotare?", "Dove prenotare?", "Quando prenotare?" (use knowledge_base, NOT transfer)
* **Default rule:**
  Se la domanda **non riguarda** prezzi, sport, codici visita, prenotazioni, sedi, orari o disponibilità → usa **knowledge_base(question)**.

---

## **6. Decision Flow (Compressed)**

1. Identify intent.
2. Select the correct function.
3. Ask for missing parameters.
4. Call the function.
5. If no answer → explain + ask if they want a human.
6. **Never greet.**

---

## **7. CRITICAL - Booking vs Transfer**

**Questions ABOUT booking process** → Use **query_knowledge_base**:
* "Come prenotare un esame?"
* "Dove si prenota?"
* "Quando posso prenotare?"
* "Quali sono gli orari per prenotare?"

**ACTUAL booking requests** → Use **request_transfer** with reason='booking request':
* "Voglio prenotare un esame"
* "Prenota per me una visita"
* "Devo prenotare X"
* "Posso prenotare ora?"

---

## **8. Communication Style**

* Italian, short, clear, professional.
* Use light fillers ("uhm…", "vediamo…").
* Time format in Italian ("alle sette e trenta", "da otto a dodici").
* Summarize user input before calling functions.
* Never give medical advice.

---

## **9. Key Principles**

* No greetings.
* No improvisation.
* Fill all parameters.
* Ask permission before any transfer.
* Only use the defined functions.
* Italian only.
"""
    
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