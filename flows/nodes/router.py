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
You are the initial contact point for the INFO MODE service.

You provide information about:
- Services, prices, clinic hours, exam requirements
- Documents, forms, and general healthcare questions
- Sports medicine visits and diagnostics

Listen carefully to the user's request and route them to the info agent.
{settings.language_config}"""
        }],
        task_messages=[{
            "role": "system",
            "content": f"""Greet the caller warmly: 'Ciao, sono Ualà, assistente virtuale di Cerba Healthcare. Come posso aiutarti oggi?'

Then listen to their response:
- For casual greetings (hello, hi, hey, ciao) → respond naturally and ask how you can help
- For actual questions about services, prices, hours, exams → call route_to_info with their exact question

Examples:
- User: "Ciao" → You: "Ciao! Come posso aiutarti oggi?"
- User: "Quanto costa un esame del sangue?" → route_to_info(user_query: "Quanto costa un esame del sangue?")
- User: "Che ore siete aperti?" → route_to_info(user_query: "Che ore siete aperti?")

{settings.language_config}"""
        }],
        functions=[
            # ========================================
            # 🚫 BOOKING DISABLED FOR LOMBARDY RELEASE
            # ========================================
            # To re-enable booking: Simply uncomment this function
            # FlowsFunctionSchema(
            #     name="route_to_booking",
            #     handler=route_to_booking_handler,
            #     description="Route to booking agent when user wants to book an appointment or medical service. Use when user mentions booking, appointment, prenota, visita, esame, or similar booking-related terms.",
            #     properties={
            #         "user_request": {
            #             "type": "string",
            #             "description": "What the user wants to book (e.g., 'X-ray', 'blood test', 'cardiology visit')"
            #         }
            #     },
            #     required=["user_request"]
            # ),

            FlowsFunctionSchema(
                name="route_to_info",
                handler=route_to_info_handler,
                description="Route to info agent when user asks actual questions about services, prices, clinic hours, exam requirements, documents, or any healthcare-related questions. Pass their exact question.",
                properties={
                    "user_query": {
                        "type": "string",
                        "description": "The exact question the user asked (e.g., 'Quanto costa un esame del sangue?', 'Che ore siete aperti?', 'Devo fare una radiografia')"
                    }
                },
                required=["user_query"]
            )
        ],
        respond_immediately=True  # Bot speaks first
    )
