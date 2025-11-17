"""
Transfer Handlers
Handles transfer to human operator and follow-up questions
"""

import asyncio
from typing import Tuple, Dict, Any
from loguru import logger

from pipecat_flows import FlowManager, NodeConfig, FlowArgs


async def request_transfer_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Handle transfer to human operator
    
    Args:
        args: Function arguments with reason
        flow_manager: Flow manager instance
        
    Returns:
        Tuple of (result dict, transfer node)
    """
    try:
        reason = args.get("reason", "user request").strip()
        
        logger.info(f"📞 Transfer requested: {reason}")
        
        # Store transfer information in flow state
        flow_manager.state["transfer_requested"] = True
        flow_manager.state["transfer_reason"] = reason
        flow_manager.state["transfer_timestamp"] = str(asyncio.get_event_loop().time())
        
        # Note: Actual escalation API call will be handled by the main.py
        # when the pipeline ends, similar to booking agent's escalation flow
        
        logger.success(f"✅ Transfer initiated: {reason}")
        
        # Transition to transfer node
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {
            "success": True,
            "reason": reason,
            "message": "Transferring to human operator"
        }, create_transfer_node()
        
    except Exception as e:
        logger.error(f"❌ Transfer handler error: {e}")
        
        # Even on error, still transfer (safe fallback)
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {
            "success": True,
            "reason": "error in transfer handler",
            "error": str(e)
        }, create_transfer_node()


async def check_followup_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Check if user needs more help or wants to end conversation
    Used in answer node after providing information
    
    Args:
        args: Function arguments with needs_more_help boolean
        flow_manager: Flow manager instance
        
    Returns:
        Tuple of (result dict, next node)
    """
    try:
        needs_more_help = args.get("needs_more_help", False)
        
        logger.info(f"🔄 Follow-up check: needs_more_help={needs_more_help}")
        
        # Store in flow state
        flow_manager.state["follow_up_requested"] = needs_more_help
        
        if needs_more_help:
            # Return to greeting node with all tools available
            logger.info("🔄 User needs more help - returning to greeting")
            
            from info_agent.flows.nodes.greeting import create_greeting_node
            return {
                "needs_more_help": True,
                "action": "continue conversation"
            }, create_greeting_node(flow_manager)
        else:
            # End conversation gracefully
            logger.info("👋 User satisfied - ending conversation")
            
            from info_agent.flows.nodes.answer import create_goodbye_node
            return {
                "needs_more_help": False,
                "action": "end conversation"
            }, create_goodbye_node()
            
    except Exception as e:
        logger.error(f"❌ Follow-up handler error: {e}")
        
        # On error, default to goodbye (safe fallback)
        from info_agent.flows.nodes.answer import create_goodbye_node
        return {
            "error": str(e),
            "action": "end conversation (error)"
        }, create_goodbye_node()