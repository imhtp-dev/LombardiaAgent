"""
Exam List Handlers
Handles queries for exam lists by visit type or sport
"""

from typing import Tuple, Dict, Any
from loguru import logger

from pipecat_flows import FlowManager, NodeConfig, FlowArgs


async def choose_exam_query_type_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Determine if user wants exams by visit type or by sport
    """
    try:
        query_type = args.get("query_type", "").strip()
        
        logger.info(f"📋 Exam list - Query type: {query_type}")
        flow_manager.state["exam_query_type"] = query_type
        
        if query_type == "by_visit_type":
            # Route to visit type collection
            from info_agent.flows.nodes.exam_list import create_collect_visit_type_node
            return {
                "query_type": query_type
            }, create_collect_visit_type_node()
        
        elif query_type == "by_sport":
            # Route to sport name collection
            from info_agent.flows.nodes.exam_list import create_collect_sport_name_node
            return {
                "query_type": query_type
            }, create_collect_sport_name_node()
        
        else:
            logger.warning(f"⚠️ Unknown exam query type: {query_type}")
            # Default to visit type
            from info_agent.flows.nodes.exam_list import create_collect_visit_type_node
            return {
                "query_type": "by_visit_type",
                "note": "defaulted to visit type"
            }, create_collect_visit_type_node()
            
    except Exception as e:
        logger.error(f"❌ Error in exam query type handler: {e}")
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {"success": False, "error": str(e)}, create_transfer_node()


async def record_visit_type_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Record visit type and move to result node
    """
    try:
        visit_type = args.get("visit_type", "").strip().upper()
        
        logger.info(f"📝 Exam list - Recorded visit type: {visit_type}")
        flow_manager.state["exam_visit_type"] = visit_type
        
        # Move to result node
        from info_agent.flows.nodes.exam_list import create_exam_list_result_node
        return {
            "visit_type": visit_type
        }, create_exam_list_result_node()
        
    except Exception as e:
        logger.error(f"❌ Error recording visit type: {e}")
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {"success": False, "error": str(e)}, create_transfer_node()


async def record_sport_name_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Record sport name and move to result node
    """
    try:
        sport = args.get("sport", "").strip()
        
        logger.info(f"📝 Exam list - Recorded sport: {sport}")
        flow_manager.state["exam_sport"] = sport
        
        # Move to result node
        from info_agent.flows.nodes.exam_list import create_exam_list_result_node
        return {
            "sport": sport
        }, create_exam_list_result_node()
        
    except Exception as e:
        logger.error(f"❌ Error recording sport name: {e}")
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {"success": False, "error": str(e)}, create_transfer_node()


async def get_exam_list_final_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Call exam list API with parameters from state
    """
    try:
        query_type = flow_manager.state.get("exam_query_type", "")
        
        if query_type == "by_visit_type":
            # Get exam list by visit type
            visit_type = flow_manager.state.get("exam_visit_type", "")
            
            if not visit_type:
                logger.error("❌ No visit type in state")
                from info_agent.flows.nodes.transfer import create_transfer_node
                return {
                    "success": False,
                    "error": "Missing visit type"
                }, create_transfer_node()
            
            logger.info(f"📋 Getting exam list for visit type: {visit_type}")
            
            # Call exam service
            from info_agent.services.exam_service import exam_service
            result = await exam_service.get_exams_by_visit_type(visit_type)
            
            # Clean up state
            flow_manager.state.pop("exam_query_type", None)
            flow_manager.state.pop("exam_visit_type", None)
        
        elif query_type == "by_sport":
            # Get exam list by sport
            sport = flow_manager.state.get("exam_sport", "")
            
            if not sport:
                logger.error("❌ No sport in state")
                from info_agent.flows.nodes.transfer import create_transfer_node
                return {
                    "success": False,
                    "error": "Missing sport"
                }, create_transfer_node()
            
            logger.info(f"📋 Getting exam list for sport: {sport}")
            
            # Call exam service
            from info_agent.services.exam_service import exam_service
            result = await exam_service.get_exams_by_sport(sport)
            
            # Clean up state
            flow_manager.state.pop("exam_query_type", None)
            flow_manager.state.pop("exam_sport", None)
        
        else:
            logger.error(f"❌ Unknown exam query type: {query_type}")
            from info_agent.flows.nodes.transfer import create_transfer_node
            return {
                "success": False,
                "error": "Unknown query type"
            }, create_transfer_node()
        
        # Process result
        if result.success:
            logger.success(f"✅ Exam list retrieved")
            
            # Move to answer node
            from info_agent.flows.nodes.answer import create_answer_node
            return {
                "success": True,
                "exams": result.exams,
                "details": result.details
            }, create_answer_node()
        else:
            logger.error(f"❌ Exam service API failed: {result.error}")
            
            from info_agent.flows.nodes.transfer import create_transfer_node
            return {
                "success": False,
                "error": result.error
            }, create_transfer_node()
            
    except Exception as e:
        logger.error(f"❌ Exam list handler error: {e}")
        import traceback
        traceback.print_exc()
        
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {"success": False, "error": str(e)}, create_transfer_node()


# ============================================================================
# LEGACY HANDLERS (kept for backward compatibility, but deprecated)
# ============================================================================

async def get_exams_by_visit_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    DEPRECATED: Old handler - redirects to new flow
    """
    logger.warning("⚠️ DEPRECATED: get_exams_by_visit_handler called - redirecting to new flow")
    
    visit_type = args.get("visit_type", "").strip()
    
    if visit_type:
        flow_manager.state["exam_query_type"] = "by_visit_type"
        flow_manager.state["exam_visit_type"] = visit_type
        
        from info_agent.flows.nodes.exam_list import create_exam_list_result_node
        return {
            "redirect": "has visit type"
        }, create_exam_list_result_node()
    else:
        flow_manager.state["exam_query_type"] = "by_visit_type"
        
        from info_agent.flows.nodes.exam_list import create_collect_visit_type_node
        return {
            "redirect": "collecting visit type"
        }, create_collect_visit_type_node()


async def get_exams_by_sport_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    DEPRECATED: Old handler - redirects to new flow
    """
    logger.warning("⚠️ DEPRECATED: get_exams_by_sport_handler called - redirecting to new flow")
    
    sport = args.get("sport", "").strip()
    
    if sport:
        flow_manager.state["exam_query_type"] = "by_sport"
        flow_manager.state["exam_sport"] = sport
        
        from info_agent.flows.nodes.exam_list import create_exam_list_result_node
        return {
            "redirect": "has sport"
        }, create_exam_list_result_node()
    else:
        flow_manager.state["exam_query_type"] = "by_sport"
        
        from info_agent.flows.nodes.exam_list import create_collect_sport_name_node
        return {
            "redirect": "collecting sport name"
        }, create_collect_sport_name_node()
