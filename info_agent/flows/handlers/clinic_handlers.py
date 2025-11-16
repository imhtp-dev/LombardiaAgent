"""
Clinic Info Handlers
CRITICAL: Always asks for location first per client requirement
"When requesting Summer Closures or Blood Collection Times, ALWAYS ask for the location"
"""

from typing import Tuple, Dict, Any
from loguru import logger

from pipecat_flows import FlowManager, NodeConfig, FlowArgs


async def record_location_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    CRITICAL HANDLER: Record location and move to API call
    
    Client requirement enforced here:
    Example: "Hi, are you having summer closures?"
    Bot asks: "Which location?"
    User: "Novara"
    -> This handler records "Novara" and calls API
    """
    try:
        location = args.get("location", "").strip()
        
        if not location:
            logger.warning("⚠️ Empty location received")
            # Stay in same node to re-ask
            return {
                "success": False,
                "error": "No location provided"
            }, None
        
        logger.info(f"📍 Clinic info - Recorded location: {location}")
        flow_manager.state["clinic_info_location"] = location
        
        # Extract info_type from initial_details if available
        initial_details = flow_manager.state.get("initial_details", "")
        logger.info(f"📝 Initial details: {initial_details[:100] if initial_details else 'None'}")
        
        # Store for API call
        flow_manager.state["clinic_info_query"] = initial_details or "general information"
        
        # Move to result node to call API
        logger.info(f"→ Moving to clinic info result node")
        from info_agent.flows.nodes.clinic_info import create_clinic_info_result_node
        return {
            "location": location,
            "query_type": initial_details or "general"
        }, create_clinic_info_result_node()
        
    except Exception as e:
        logger.error(f"❌ Error recording location: {e}")
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {"success": False, "error": str(e)}, create_transfer_node()


async def get_clinic_info_final_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Call clinic info API (call_graph endpoint) with location and query
    
    API expects: {"q": "query including location"}
    Example: {"q": "Summer closures, Novara location"}
    """
    try:
        # Get location and query from state
        location = flow_manager.state.get("clinic_info_location", "")
        query_type = flow_manager.state.get("clinic_info_query", "")
        
        if not location:
            logger.error("❌ No location in state - this shouldn't happen!")
            from info_agent.flows.nodes.transfer import create_transfer_node
            return {
                "success": False,
                "error": "Missing location information"
            }, create_transfer_node()
        
        # Build query string for API
        # Format: "query type, location"
        # Examples:
        # - "Summer closures, Novara location"
        # - "Blood collection times, Biella location"
        # - "Opening hours, Milano location"
        
        if query_type and query_type != "general information":
            api_query = f"{query_type}, {location} location"
        else:
            # Generic query if info type not clear
            api_query = f"{location} clinic information"
        
        logger.info(f"🏥 Calling clinic info API:")
        logger.info(f"   Location: {location}")
        logger.info(f"   Query: {api_query}")
        
        # Call clinic info service
        from info_agent.services.clinic_info_service import clinic_info_service
        result = await clinic_info_service.get_clinic_info(api_query)
        
        if result.success:
            logger.success(f"✅ Clinic info retrieved for {location}")
            
            # Clean up state
            flow_manager.state.pop("clinic_info_location", None)
            flow_manager.state.pop("clinic_info_query", None)
            
            # Move to answer node
            from info_agent.flows.nodes.answer import create_answer_node
            return {
                "success": True,
                "location": location,
                "info": result.info,
                "answer": result.answer
            }, create_answer_node()
        else:
            logger.error(f"❌ Clinic info API failed: {result.error}")
            
            # Offer transfer on API failure
            from info_agent.flows.nodes.transfer import create_transfer_node
            return {
                "success": False,
                "error": result.error
            }, create_transfer_node()
            
    except Exception as e:
        logger.error(f"❌ Clinic info handler error: {e}")
        import traceback
        traceback.print_exc()
        
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {"success": False, "error": str(e)}, create_transfer_node()


# ============================================================================
# LEGACY HANDLER (kept for backward compatibility, but deprecated)
# ============================================================================

async def get_clinic_info_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    DEPRECATED: Old handler that expected location + info_type together
    Redirects to location collection flow
    """
    logger.warning("⚠️ DEPRECATED: get_clinic_info_handler called - redirecting to location flow")
    
    location = args.get("location", "").strip()
    info_type = args.get("info_type", "").strip()
    
    if location and info_type:
        # Both provided - store and go to result
        flow_manager.state["clinic_info_location"] = location
        flow_manager.state["clinic_info_query"] = info_type
        
        from info_agent.flows.nodes.clinic_info import create_clinic_info_result_node
        return {
            "redirect": "both params provided"
        }, create_clinic_info_result_node()
    elif location:
        # Only location - store and go to result with generic query
        flow_manager.state["clinic_info_location"] = location
        flow_manager.state["clinic_info_query"] = info_type or "general information"
        
        from info_agent.flows.nodes.clinic_info import create_clinic_info_result_node
        return {
            "redirect": "location provided"
        }, create_clinic_info_result_node()
    else:
        # No location - redirect to location collection
        if info_type:
            flow_manager.state["clinic_info_query"] = info_type
        
        from info_agent.flows.nodes.clinic_info import create_collect_location_node
        return {
            "redirect": "collecting location"
        }, create_collect_location_node()
