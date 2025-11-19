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

        # Run transfer escalation NOW (before returning transfer node)
        logger.info("🚀 Running transfer escalation before transition...")
        await handle_transfer_escalation(flow_manager)

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
            
            from info_agent.flows.nodes.conversation import create_greeting_node
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


async def handle_transfer_escalation(
    flow_manager: FlowManager
) -> None:
    """
    Handle escalation API call for transfer to human operator

    Called AFTER agent says transfer message, BEFORE call ends
    This runs early analysis and calls the bridge escalation API

    Flow:
    1. Get call_extractor from flow_manager.state
    2. Run early analysis (LLM analyzes transcript NOW)
    3. Call bridge escalation API with analysis data
    4. Store analysis for later Supabase save
    5. If API fails: end call anyway (per requirement)

    Note: WebSocket closes automatically after escalation API call

    Args:
        flow_manager: Flow manager instance
    """
    try:
        logger.info("🚀 Starting transfer escalation process...")

        # Get call_extractor and session_id from flow state
        call_extractor = flow_manager.state.get("call_extractor")
        session_id = flow_manager.state.get("session_id")

        if not call_extractor:
            logger.error("❌ No call_extractor found in flow_state")
            return

        if not session_id:
            logger.error("❌ No session_id found in flow_state")
            return

        logger.info(f"📋 Running early analysis for call {session_id}...")

        # Run analysis NOW (before WebSocket closes)
        analysis = await call_extractor.analyze_for_transfer(flow_manager.state)

        logger.success("✅ Transfer analysis complete")
        logger.info(f"   Summary: {analysis['summary'][:100]}...")
        logger.info(f"   Sentiment: {analysis['sentiment']}")
        logger.info(f"   Service: {analysis['service']}")
        logger.info(f"   Duration: {analysis['duration_seconds']}s")

        # Get stream_sid from flow state (Talkdesk stream ID)
        stream_sid = flow_manager.state.get("stream_sid", "")

        # Call escalation API (WebSocket closes automatically)
        logger.info("📞 Calling bridge escalation API...")

        from info_agent.services.escalation_service import call_escalation_api

        success = await call_escalation_api(
            summary=analysis["summary"][:250],  # Ensure max 250 chars
            sentiment=analysis["sentiment"],
            action="transfer",
            duration=str(analysis["duration_seconds"]),
            service=analysis["service"],
            call_id=session_id,  # Session ID for database row matching
            stream_sid=stream_sid  # ✅ Talkdesk stream SID for direct escalation
        )

        # Store analysis for Supabase (happens after WebSocket closes)
        flow_manager.state["transfer_analysis"] = analysis
        flow_manager.state["transfer_api_success"] = success

        if success:
            logger.success(f"✅ Escalation API call successful for {session_id}")
            logger.info("🔌 WebSocket will close automatically (handled by bridge)")
        else:
            logger.error(f"❌ Escalation API call failed for {session_id}")
            logger.warning("⚠️ Ending call anyway per requirement")

    except Exception as e:
        logger.error(f"❌ Transfer escalation error: {e}")
        import traceback
        traceback.print_exc()

        # Store error in flow state but still end call
        flow_manager.state["transfer_escalation_error"] = str(e)
        logger.warning("⚠️ Ending call despite escalation error")