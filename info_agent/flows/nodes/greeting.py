"""
Greeting Node - One-Shot Agent Architecture
Single conversation node with ALL 6 API tools available.
LLM handles: intent detection, parameter collection, API calls, and responses.
"""

from pipecat_flows import NodeConfig, FlowsFunctionSchema, FlowManager
from info_agent.config.settings import info_settings
from loguru import logger


def create_greeting_node(flow_manager: FlowManager = None) -> NodeConfig:
    """
    One-shot agent greeting node with ALL 6 API tools.

    Architecture:
    - LLM naturally detects user intent from conversation
    - LLM asks for missing parameters conversationally
    - LLM calls appropriate API when all params collected
    - Returns to same node after API call (enables follow-up questions)

    No complex flow routing - LLM handles everything via function calling.
    """
    from info_agent.flows.handlers.api_handlers import (
        query_knowledge_base_handler,
        get_competitive_pricing_handler,
        get_non_competitive_pricing_handler,
        get_exam_by_visit_handler,
        get_exam_by_sport_handler,
        get_clinic_info_handler
    )
    from info_agent.flows.handlers.transfer_handlers import request_transfer_handler
    from flows.handlers.agent_routing_handlers import transfer_from_info_to_booking_handler

    # ✅ Get business_status from flow state (passed from TalkDesk via bridge)
    business_status = None
    if flow_manager:
        business_status = flow_manager.state.get("business_status")

    # ✅ Validate and log business_status
    if not business_status:
        logger.error("❌ CRITICAL: business_status not found in flow_manager.state!")
        logger.error("   Transfer behavior will be incorrect - defaulting to 'close' (safe fallback)")
        business_status = "close"  # Safe fallback - no transfers when unsure
    else:
        logger.success(f"✅ Business status loaded from flow state: {business_status.upper()}")

    return NodeConfig(
        name="greeting",
        role_messages=[
            {
                "role": "system",
                "content": info_settings.get_system_prompt(business_status)  # ✅ Dynamic prompt with business_status
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": f"""You are Ualà, Cerba Healthcare's information assistant.

Your task: Warmly greet callers and help them with medical information using ONLY the available functions.

Communication style:
- Greet warmly in {info_settings.agent_config['language']}
- Ask ONE question at a time
- Collect parameters naturally through conversation
- Call functions ONLY when all required parameters are collected
- After providing information, ask if they need more help

CRITICAL RULES:
1. NEVER use your own knowledge - ALWAYS use functions
2. For clinic info (hours/closures), call get_clinic_info with user's natural language query
3. Collect pricing parameters step-by-step: age → gender → sport → region
4. If information not found, offer transfer to human operator
5. Stay in conversation loop for follow-up questions

Available tools:
- query_knowledge_base: FAQs, documents, forms, preparation
- get_competitive_pricing: Agonistic visit prices (needs: age, gender, sport, region)
- get_non_competitive_pricing: Non-agonistic prices (needs: ecg_under_stress)
- get_exam_by_visit: Exam list by visit code (A1-A3, B1-B5)
- get_exam_by_sport: Exam list by sport name
- get_clinic_info: Hours, closures, blood times, doctors (needs: natural language query with location)
- transfer_to_booking_agent: Transfer to booking agent when user wants to book appointment
- request_transfer: Transfer to human operator when needed"""
            }
        ],
        functions=[
            # ================================================================
            # TOOL 1: Knowledge Base Query
            # ================================================================
            FlowsFunctionSchema(
                name="query_knowledge_base",
                handler=query_knowledge_base_handler,
                description="Search knowledge base for FAQs, documents, forms, preparation instructions, general medical information about Cerba Healthcare services",
                properties={
                    "query": {
                        "type": "string",
                        "description": "Natural language question to search in knowledge base (e.g., 'Quali documenti servono per visita sportiva?', 'Preparazione esami sangue')"
                    }
                },
                required=["query"]
            ),

            # ================================================================
            # TOOL 2: Competitive (Agonistic) Pricing
            # ================================================================
            FlowsFunctionSchema(
                name="get_competitive_pricing",
                handler=get_competitive_pricing_handler,
                description="Get price for agonistic sports medical visit. Requires ALL 4 parameters. Ask user step-by-step if any are missing.",
                properties={
                    "age": {
                        "type": "integer",
                        "description": "Athlete's age in years (e.g., 15, 18, 25)"
                    },
                    "gender": {
                        "type": "string",
                        "enum": ["M", "F"],
                        "description": "Gender: 'M' for male (maschio), 'F' for female (femmina)"
                    },
                    "sport": {
                        "type": "string",
                        "description": "Sport name in Italian (e.g., 'calcio', 'nuoto', 'pallavolo', 'basket', 'tennis')"
                    },
                    "region": {
                        "type": "string",
                        "description": "Italian region or province (e.g., 'Piemonte', 'Torino', 'Novara', 'Biella')"
                    }
                },
                required=["age", "gender", "sport", "region"]
            ),

            # ================================================================
            # TOOL 3: Non-Competitive (Non-Agonistic) Pricing
            # ================================================================
            FlowsFunctionSchema(
                name="get_non_competitive_pricing",
                handler=get_non_competitive_pricing_handler,
                description="Get price for non-agonistic sports medical visit (for gym, recreational sports). Ask user if they need ECG under stress.",
                properties={
                    "ecg_under_stress": {
                        "type": "boolean",
                        "description": "True if ECG under stress (ECG sotto sforzo) is needed, False for just resting ECG"
                    }
                },
                required=["ecg_under_stress"]
            ),

            # ================================================================
            # TOOL 4: Exam List by Visit Type
            # ================================================================
            FlowsFunctionSchema(
                name="get_exam_by_visit",
                handler=get_exam_by_visit_handler,
                description="Get list of required exams for a specific visit type code. Use when user mentions visit codes like A1, A2, B1, etc.",
                properties={
                    "visit_type": {
                        "type": "string",
                        "enum": ["A1", "A2", "A3", "B1", "B2", "B3", "B4", "B5"],
                        "description": "Visit type code (A1, A2, A3 for agonistic; B1-B5 for non-agonistic)"
                    }
                },
                required=["visit_type"]
            ),

            # ================================================================
            # TOOL 5: Exam List by Sport
            # ================================================================
            FlowsFunctionSchema(
                name="get_exam_by_sport",
                handler=get_exam_by_sport_handler,
                description="Get list of required exams for a specific sport. Use when user asks what exams are needed for their sport.",
                properties={
                    "sport": {
                        "type": "string",
                        "description": "Sport name in Italian (e.g., 'calcio', 'nuoto', 'pallavolo', 'ciclismo', 'atletica')"
                    }
                },
                required=["sport"]
            ),

            # ================================================================
            # TOOL 6: Clinic Information
            # ================================================================
            FlowsFunctionSchema(
                name="get_clinic_info",
                handler=get_clinic_info_handler,
                description="Get clinic information: hours, closures, blood collection times, doctor names, etc. Pass the user's request as natural language query including location.",
                properties={
                    "query": {
                        "type": "string",
                        "description": "Natural language query including location (e.g., 'orari della sede di Biella', 'chiusure estive Novara', 'medici cardiologi a Milano', 'orari prelievi Torino')"
                    }
                },
                required=["query"]
            ),

            # ================================================================
            # TOOL 7: Transfer to Booking Agent
            # ================================================================
            FlowsFunctionSchema(
                name="transfer_to_booking_agent",
                handler=transfer_from_info_to_booking_handler,
                description="Transfer to booking agent when user wants to book an appointment or medical service. Use when user mentions booking, prenota, appointment, visita, esame, or wants to schedule any medical service.",
                properties={
                    "user_request": {
                        "type": "string",
                        "description": "What the user wants to book (e.g., 'blood test', 'cardiology visit', 'X-ray', 'sports medical examination')"
                    }
                },
                required=["user_request"]
            ),

            # ================================================================
            # TOOL 8: Transfer to Human Operator
            # ================================================================
            FlowsFunctionSchema(
                name="request_transfer",
                handler=request_transfer_handler,
                description="Transfer call to human operator. Use when: information not found in functions, user explicitly requests human assistance, SSN/agreement questions, or cannot help with available tools. NOTE: For booking appointments, use transfer_to_booking_agent instead.",
                properties={
                    "reason": {
                        "type": "string",
                        "description": "Reason for transfer (e.g., 'information not found', 'user request', 'SSN question', 'technical issue')"
                    }
                },
                required=["reason"]
            )
        ],
        respond_immediately=True  # ✅ Bot speaks first when conversation starts
    )
