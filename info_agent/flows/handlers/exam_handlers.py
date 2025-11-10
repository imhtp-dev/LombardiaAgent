"""
Exam Handlers
Handles exam requirement queries by visit type or sport
"""

from typing import Tuple, Dict, Any
from loguru import logger

from pipecat_flows import FlowManager, NodeConfig, FlowArgs


async def get_exams_by_visit_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Get exam list for a specific visit type
    
    Args:
        args: Function arguments with visit_type
        flow_manager: Flow manager instance
        
    Returns:
        Tuple of (result dict, next node)
    """
    try:
        visit_type = args.get("visit_type", "").strip().upper()
        
        if not visit_type:
            logger.warning("⚠️ Missing visit_type parameter")
            return {
                "success": False,
                "error": "Please specify the visit type"
            }, None
        
        logger.info(f"🔬 Getting exams for visit type: {visit_type}")
        
        # Query exam service
        from info_agent.services.exam_service import exam_service
        result = await exam_service.get_exams_by_visit_type(visit_type)
        
        # Store in flow state
        flow_manager.state["last_exam_query"] = {
            "type": "by_visit",
            "visit_type": visit_type,
            "exams": result.exams
        }
        
        if result.success:
            logger.success(f"✅ Found {len(result.exams)} exams for visit type {visit_type}")
            
            # Return to answer node
            from info_agent.flows.nodes.answer import create_answer_node
            return {
                "success": True,
                "visit_type": visit_type,
                "exams": result.exams,
                "exam_count": len(result.exams)
            }, create_answer_node()
        else:
            # API failed - offer transfer
            logger.error(f"❌ Exam query failed: {result.error}")
            
            from info_agent.flows.nodes.transfer import create_transfer_node
            return {
                "success": False,
                "error": result.error
            }, create_transfer_node()
            
    except Exception as e:
        logger.error(f"❌ Exam by visit handler error: {e}")
        
        # On error, offer transfer
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {
            "success": False,
            "error": str(e)
        }, create_transfer_node()


async def get_exams_by_sport_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Get exam list for a specific sport
    
    Args:
        args: Function arguments with sport
        flow_manager: Flow manager instance
        
    Returns:
        Tuple of (result dict, next node)
    """
    try:
        sport = args.get("sport", "").strip()
        
        if not sport:
            logger.warning("⚠️ Missing sport parameter")
            return {
                "success": False,
                "error": "Please specify the sport"
            }, None
        
        logger.info(f"🔬 Getting exams for sport: {sport}")
        
        # Query exam service
        from info_agent.services.exam_service import exam_service
        result = await exam_service.get_exams_by_sport(sport)
        
        # Store in flow state
        flow_manager.state["last_exam_query"] = {
            "type": "by_sport",
            "sport": sport,
            "exams": result.exams
        }
        
        if result.success:
            logger.success(f"✅ Found {len(result.exams)} exams for sport '{sport}'")
            
            # Return to answer node
            from info_agent.flows.nodes.answer import create_answer_node
            return {
                "success": True,
                "sport": sport,
                "exams": result.exams,
                "exam_count": len(result.exams)
            }, create_answer_node()
        else:
            # API failed - offer transfer
            logger.error(f"❌ Exam query failed: {result.error}")
            
            from info_agent.flows.nodes.transfer import create_transfer_node
            return {
                "success": False,
                "error": result.error
            }, create_transfer_node()
            
    except Exception as e:
        logger.error(f"❌ Exam by sport handler error: {e}")
        
        # On error, offer transfer
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {
            "success": False,
            "error": str(e)
        }, create_transfer_node()