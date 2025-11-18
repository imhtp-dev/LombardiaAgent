"""
Agent Routing Handlers
Handles routing between booking agent and info agent
"""

from typing import Dict, Any, Tuple
from pipecat_flows import FlowManager, NodeConfig
from loguru import logger


async def route_to_booking_handler(
    args: Dict[str, Any],
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Route to booking agent flow.
    This is called when:
    1. User initially requests booking from router
    2. User requests booking from info agent

    Args:
        args: Contains user_request (what they want to book)
        flow_manager: Flow manager instance

    Returns:
        Tuple of (result dict, booking greeting node)
    """
    user_request = args.get("user_request", "")

    logger.info(f"🟢 Routing to BOOKING agent | User request: {user_request}")

    # Update state to track current agent
    flow_manager.state["current_agent"] = "booking"
    flow_manager.state["booking_in_progress"] = False  # Will be set to True once booking starts
    flow_manager.state["can_transfer_to_info"] = False  # Block info transfers during booking
    flow_manager.state["came_from_agent"] = flow_manager.state.get("current_agent", "router")

    # Store the user's initial request for the booking flow
    if user_request:
        flow_manager.state["initial_booking_request"] = user_request

    logger.info(f"📊 State updated: current_agent=booking, booking_in_progress=False")

    # Import and return booking greeting node
    from flows.nodes.greeting import create_greeting_node

    return {
        "routed_to": "booking_agent",
        "user_request": user_request,
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }, create_greeting_node()


async def route_to_info_handler(
    args: Dict[str, Any],
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Route to info agent flow.
    This is called when:
    1. User initially requests info from router
    2. User requests info from booking completion node

    Args:
        args: Contains question_type (what kind of info they need)
        flow_manager: Flow manager instance

    Returns:
        Tuple of (result dict, info greeting node)
    """
    question_type = args.get("question_type", "")

    logger.info(f"🟠 Routing to INFO agent | Question type: {question_type}")

    # Update state to track current agent
    previous_agent = flow_manager.state.get("current_agent", "router")
    flow_manager.state["current_agent"] = "info"
    flow_manager.state["booking_in_progress"] = False
    flow_manager.state["can_transfer_to_booking"] = True  # Info can always transfer to booking
    flow_manager.state["came_from_agent"] = previous_agent

    # Store the question type for context
    if question_type:
        flow_manager.state["initial_question_type"] = question_type

    # Initialize call_extractor for info agent (Supabase storage)
    session_id = flow_manager.state.get("session_id", "unknown")
    from info_agent.services.call_data_extractor import get_call_extractor
    call_extractor = get_call_extractor(session_id)
    flow_manager.state["call_extractor"] = call_extractor
    logger.info(f"📊 State updated: current_agent=info, call_extractor initialized, can_transfer_to_booking=True")

    # Import and return info greeting node
    from info_agent.flows.nodes.greeting import create_greeting_node as create_info_greeting_node

    return {
        "routed_to": "info_agent",
        "question_type": question_type,
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }, create_info_greeting_node(flow_manager)


async def transfer_from_info_to_booking_handler(
    args: Dict[str, Any],
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Transfer from info agent to booking agent.
    This can be called ANYTIME during info agent flow.

    Args:
        args: Contains reason for transfer (optional)
        flow_manager: Flow manager instance

    Returns:
        Tuple of (result dict, booking greeting node)
    """
    reason = args.get("reason", "User requested booking")
    user_request = args.get("user_request", "")

    logger.info(f"🟠➜🟢 Transferring from INFO to BOOKING | Reason: {reason}")

    # Update state
    flow_manager.state["previous_agent"] = "info"
    flow_manager.state["current_agent"] = "booking"
    flow_manager.state["transfer_reason"] = reason
    flow_manager.state["booking_in_progress"] = False  # Will be set to True once booking starts
    flow_manager.state["can_transfer_to_info"] = False

    if user_request:
        flow_manager.state["initial_booking_request"] = user_request

    logger.success(f"✅ Transfer complete: INFO → BOOKING")

    # Import and return booking greeting node
    from flows.nodes.greeting import create_greeting_node

    return {
        "transfer": "info_to_booking",
        "reason": reason,
        "user_request": user_request,
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }, create_greeting_node()


async def transfer_from_booking_to_info_handler(
    args: Dict[str, Any],
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Transfer from booking agent to info agent.
    This can ONLY be called AFTER booking completion.

    Args:
        args: Contains user_question (what they want to know)
        flow_manager: Flow manager instance

    Returns:
        Tuple of (result dict, info greeting node)
    """
    user_question = args.get("user_question", "")

    # Safety check: only allow if booking is completed
    booking_completed = flow_manager.state.get("booking_completed", False)
    booking_in_progress = flow_manager.state.get("booking_in_progress", False)

    if booking_in_progress and not booking_completed:
        logger.error(f"❌ BLOCKED: Cannot transfer to INFO during active booking")
        # Return error - stay in current node
        from flows.nodes.booking import create_collect_datetime_node
        return {
            "error": "Cannot transfer during booking",
            "message": "Please complete the booking first"
        }, create_collect_datetime_node()

    logger.info(f"🟢➜🟠 Transferring from BOOKING to INFO | Question: {user_question}")

    # Update state
    flow_manager.state["previous_agent"] = "booking"
    flow_manager.state["current_agent"] = "info"
    flow_manager.state["transfer_reason"] = "Post-booking question"
    flow_manager.state["can_transfer_to_booking"] = True  # Allow return to booking

    if user_question:
        flow_manager.state["post_booking_question"] = user_question

    # Initialize call_extractor for info agent (Supabase storage)
    session_id = flow_manager.state.get("session_id", "unknown")
    from info_agent.services.call_data_extractor import get_call_extractor
    call_extractor = get_call_extractor(session_id)
    flow_manager.state["call_extractor"] = call_extractor

    logger.success(f"✅ Transfer complete: BOOKING → INFO (post-completion), call_extractor initialized")

    # Import and return info greeting node
    from info_agent.flows.nodes.greeting import create_greeting_node as create_info_greeting_node

    return {
        "transfer": "booking_to_info",
        "user_question": user_question,
        "post_booking": True,
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }, create_info_greeting_node(flow_manager)
