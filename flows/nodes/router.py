"""
Unified Router Node
Initial conversation node that detects user intent and routes to appropriate agent
"""

from pipecat_flows import NodeConfig, FlowsFunctionSchema
from config.settings import settings


def create_router_node() -> NodeConfig:
    """
    Create the initial router node that greets user and detects intent.
    Routes to either booking agent or info agent based on user's first request.
    """

    # Import handlers
    from flows.handlers.agent_routing_handlers import (
        route_to_booking_handler,
        route_to_info_handler
    )

    return NodeConfig(
        name="router",
        role_messages=[{
            "role": "system",
            "content": f"""You are Ualà, a helpful virtual assistant for Cerba Healthcare in Italy.
You are the initial contact point and need to understand what the caller needs.

You have two specialized modes:
1. BOOKING MODE - For users who want to book appointments/services
2. INFO MODE - For users who have questions about services, prices, clinic hours, etc.

Listen carefully to the user's first request and determine which mode they need.
{settings.language_config}"""
        }],
        task_messages=[{
            "role": "system",
            "content": f"""Greet the caller warmly: 'Ciao, sono Ualà, assistente virtuale di Cerba Healthcare. Come posso aiutarti oggi?'

Then listen to their response and determine:
- If they want to BOOK an appointment/service → call route_to_booking
- If they want INFORMATION (prices, hours, exams, documents) → call route_to_info

Examples:
- "Vorrei prenotare una visita" → route_to_booking
- "Quanto costa un esame del sangue?" → route_to_info
- "Devo fare una radiografia" → route_to_booking
- "Che ore siete aperti?" → route_to_info

{settings.language_config}"""
        }],
        functions=[
            FlowsFunctionSchema(
                name="route_to_booking",
                handler=route_to_booking_handler,
                description="Route to booking agent when user wants to book an appointment or medical service. Use when user mentions booking, appointment, prenota, visita, esame, or similar booking-related terms.",
                properties={
                    "user_request": {
                        "type": "string",
                        "description": "What the user wants to book (e.g., 'X-ray', 'blood test', 'cardiology visit')"
                    }
                },
                required=["user_request"]
            ),
            FlowsFunctionSchema(
                name="route_to_info",
                handler=route_to_info_handler,
                description="Route to info agent when user wants information about services, prices, clinic hours, exam requirements, documents, or general questions. Use when user asks questions without booking intent.",
                properties={
                    "question_type": {
                        "type": "string",
                        "description": "Type of information requested (e.g., 'pricing', 'clinic hours', 'exam requirements', 'documents', 'general info')"
                    }
                },
                required=["question_type"]
            )
        ],
        respond_immediately=True  # Bot speaks first
    )
