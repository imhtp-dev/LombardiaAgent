"""
Conversation Node - One-Shot Agent Architecture
Main conversation handler with ALL 6 API tools available.
LLM handles: intent detection, parameter collection, API calls, and responses.
Note: Router greets, this node answers questions.
"""

from pipecat_flows import NodeConfig, FlowsFunctionSchema, FlowManager
from pipecat_flows.types import ContextStrategyConfig, ContextStrategy
from info_agent.config.settings import info_settings
from loguru import logger


def create_greeting_node(flow_manager: FlowManager = None) -> NodeConfig:
    """
    Main conversation node with ALL 6 API tools.

    Architecture:
    - LLM naturally detects user intent from conversation
    - LLM asks for missing parameters conversationally
    - LLM calls appropriate API when all params collected
    - Returns to same node after API call (enables follow-up questions)

    Context Management:
    - RESET strategy when entering from router (clears router context)
    - APPEND strategy (default) when returning from function calls
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

    # ✅ Get business_status and user_query from flow state
    business_status = None
    user_query = ""
    use_reset_strategy = False

    if flow_manager:
        business_status = flow_manager.state.get("business_status")
        user_query = flow_manager.state.get("user_initial_query", "")

        # ✅ If user_query exists, we're coming from router → use RESET
        if user_query:
            logger.success(f"✅ User query from router: {user_query}")
            flow_manager.state.pop("user_initial_query", None)  # Clear to prevent re-injection
            logger.debug("🗑️ Cleared user_initial_query from state")
            use_reset_strategy = True
            logger.info("🔄 Using RESET strategy (coming from router)")
        else:
            logger.info("➕ Using APPEND strategy (returning from function call)")

    # ✅ Validate business_status
    if not business_status:
        logger.error("❌ CRITICAL: business_status not found in flow_manager.state!")
        logger.error("   Transfer behavior will be incorrect - defaulting to 'close' (safe fallback)")
        business_status = "close"
    else:
        logger.success(f"✅ Business status loaded from flow state: {business_status.upper()}")

    # Build task message - minimal, just user query injection
    # All instructions are in settings.py system prompt
    task_message = f"""User asked: "{user_query}" """ if user_query else ""

    # Build base config parameters
    base_config = {
        "name": "greeting",
        "role_messages": [{
            "role": "system",
            "content": info_settings.get_system_prompt(business_status)
        }],
        "task_messages": [{
            "role": "system",
            "content": task_message
        }],
        "functions": [
            # ================================================================
            # TOOL 1: Knowledge Base Query (Lombardia)
            # ================================================================
            FlowsFunctionSchema(
                name="knowledge_base_lombardia",
                handler=query_knowledge_base_handler,
                description="Search knowledge base for FAQs, documents, forms, preparation instructions, and general medical information",
                properties={
                    "query": {
                        "type": "string",
                        "description": "Natural language question to search in knowledge base"
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
            # TOOL 3: Non-Competitive (Non-Agonistic) Pricing (Lombardia)
            # ================================================================
            FlowsFunctionSchema(
                name="get_price_non_agonistic_visit_lombardia",
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
            # TOOL 6: Clinic Information (Lombardia - Call Graph)
            # ================================================================
            FlowsFunctionSchema(
                name="call_graph_lombardia",
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
            # TOOL 7: Transfer to Human Operator
            # ================================================================
            FlowsFunctionSchema(
                name="request_transfer",
                handler=request_transfer_handler,
                description="Transfer call to human operator when needed",
                properties={
                    "reason": {
                        "type": "string",
                        "description": "Reason for transfer"
                    }
                },
                required=["reason"]
            )
        ],
        "respond_immediately": True
    }

    # ✅ Add context_strategy conditionally
    if use_reset_strategy:
        base_config["context_strategy"] = ContextStrategyConfig(
            strategy=ContextStrategy.RESET  # Clear router context on first entry
        )

    return NodeConfig(**base_config)
