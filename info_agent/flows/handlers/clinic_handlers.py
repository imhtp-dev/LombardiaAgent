"""
Clinic Information Handlers
Handles clinic hours, locations, summer closures, blood collection times
"""

from typing import Tuple, Dict, Any
from loguru import logger

from pipecat_flows import FlowManager, NodeConfig, FlowArgs


async def get_clinic_info_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Get clinic information using call_graph API
    
    Args:
        args: Function arguments with location and info_type
        flow_manager: Flow manager instance
        
    Returns:
        Tuple of (result dict, next node)
    """
    try:
        location = args.get("location", "").strip()
        info_type = args.get("info_type", "").strip()
        
        if not location or not info_type:
            logger.warning("⚠️ Missing location or info_type parameter")
            return {
                "success": False,
                "error": "Please provide both location and information type"
            }, None
        
        logger.info(f"🏥 Getting clinic info: {info_type} for {location}")
        
        # Query clinic info service
        from info_agent.services.clinic_info_service import clinic_info_service
        result = await clinic_info_service.get_clinic_info(
            location=location,
            info_type=info_type
        )
        
        # Store in flow state
        flow_manager.state["last_clinic_query"] = {
            "location": location,
            "info_type": info_type,
            "answer": result.answer
        }
        
        if result.success:
            logger.success(f"✅ Clinic info retrieved for {location}")
            
            # Return to answer node
            from info_agent.flows.nodes.answer import create_answer_node
            return {
                "success": True,
                "location": location,
                "info_type": info_type,
                "answer": result.answer
            }, create_answer_node()
        else:
            # API failed - offer transfer
            logger.error(f"❌ Clinic info query failed: {result.error}")
            
            from info_agent.flows.nodes.transfer import create_transfer_node
            return {
                "success": False,
                "error": result.error
            }, create_transfer_node()
            
    except Exception as e:
        logger.error(f"❌ Clinic info handler error: {e}")
        
        # On error, offer transfer
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {
            "success": False,
            "error": str(e)
        }, create_transfer_node()