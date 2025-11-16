"""
Intent Identification Handlers
Identifies what the user wants and routes to appropriate flow
"""

from typing import Tuple, Dict, Any
from loguru import logger

from pipecat_flows import FlowManager, NodeConfig, FlowArgs


async def identify_intent_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Identify user's intent and route to appropriate flow
    
    Args:
        args: Function arguments with intent and optional details
        flow_manager: Flow manager instance
        
    Returns:
        Tuple of (result dict, next node based on intent)
    """
    try:
        intent = args.get("intent", "").strip()
        initial_details = args.get("initial_details", "").strip()
        
        logger.info(f"🎯 Identified intent: {intent}")
        if initial_details:
            logger.info(f"📝 Initial details: {initial_details[:100]}...")
        
        # Store intent in flow state
        flow_manager.state["user_intent"] = intent
        flow_manager.state["initial_details"] = initial_details
        
        # Route based on intent
        if intent == "general_question":
            # Knowledge base query flow
            logger.info("→ Routing to knowledge base flow")
            from info_agent.flows.nodes.knowledge_query import create_knowledge_query_node
            return {
                "intent": intent,
                "route": "knowledge_base"
            }, create_knowledge_query_node()
        
        elif intent == "competitive_pricing":
            # Agonisticapricing - collect parameters step by step
            logger.info("→ Routing to Agonistica pricing flow")
            from info_agent.flows.nodes.competitive_pricing import create_collect_age_node
            return {
                "intent": intent,
                "route": "competitive_pricing"
            }, create_collect_age_node()
        
        elif intent == "non_competitive_pricing":
            # Non-Agonisticapricing flow
            logger.info("→ Routing to non-Agonistica pricing flow")
            from info_agent.flows.nodes.non_competitive_pricing import create_collect_ecg_preference_node
            return {
                "intent": intent,
                "route": "non_competitive_pricing"
            }, create_collect_ecg_preference_node()
        
        elif intent == "clinic_info":
            # Clinic info - ALWAYS ask for location first per client requirement
            logger.info("→ Routing to clinic info flow (will ask for location)")
            from info_agent.flows.nodes.clinic_info import create_collect_location_node
            return {
                "intent": intent,
                "route": "clinic_info"
            }, create_collect_location_node()
        
        elif intent == "exam_list":
            # Exam list - determine if by visit type or sport
            logger.info("→ Routing to exam list flow")
            from info_agent.flows.nodes.exam_list import create_exam_list_choice_node
            return {
                "intent": intent,
                "route": "exam_list"
            }, create_exam_list_choice_node()
        
        elif intent == "transfer_request":
            # User explicitly wants transfer
            logger.info("→ Routing to transfer flow")
            from info_agent.flows.nodes.transfer import create_transfer_node
            return {
                "intent": intent,
                "route": "transfer"
            }, create_transfer_node()
        
        else:
            # Unknown intent - default to knowledge base
            logger.warning(f"⚠️ Unknown intent '{intent}', defaulting to knowledge base")
            from info_agent.flows.nodes.knowledge_query import create_knowledge_query_node
            return {
                "intent": "general_question",
                "route": "knowledge_base",
                "note": "Unknown intent, defaulted to knowledge base"
            }, create_knowledge_query_node()
            
    except Exception as e:
        logger.error(f"❌ Intent identification error: {e}")
        
        # On error, offer transfer
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {
            "success": False,
            "error": str(e)
        }, create_transfer_node()
