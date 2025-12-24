"""
Unified Router Node
Initial conversation node that detects user intent and routes to appropriate agent

NOTE: Booking agent is currently DISABLED. All calls route to info agent only.
"""

from pipecat_flows import NodeConfig, FlowsFunctionSchema
from config.settings import settings


def create_router_node() -> NodeConfig:
    """
    Create the initial router node that greets user and detects intent.
    Currently routes ALL calls to info agent (booking disabled).
    """

    # Import handlers
    from flows.handlers.agent_routing_handlers import (
        # route_to_booking_handler,  # DISABLED - booking agent not in use
        route_to_info_handler
    )

    return NodeConfig(
        name="router",
        role_messages=[{
            "role": "system",
            "content": f"""You are Ualà, a helpful virtual assistant for Cerba Healthcare in Italy.
You are the initial contact point for callers.

You can help with:
- Information about services, prices, clinic hours, exam requirements, documents
- Answering healthcare-related questions

NOTE: Booking is not available at this time. If user wants to book, inform them politely and offer to help with information instead.
{settings.language_config}"""
        }],
        task_messages=[{
            "role": "system",
            "content": f"""Greet the caller warmly: 'Ciao, sono Ualà, assistente virtuale di Cerba Healthcare. Come posso aiutarti oggi?'

Then listen to their response and route to info agent:

FOR INFO (use route_to_info):
- User asks questions about services, prices, hours, requirements
- User needs information
- Examples: "Quanto costa un esame?", "Che ore siete aperti?", "Cosa devo portare?"

FOR BOOKING REQUESTS:
- If user wants to book, politely explain booking is not available via this assistant
- Offer to provide information instead, then use route_to_info
- Say: "Mi dispiace, al momento non posso effettuare prenotazioni. Posso però fornirti informazioni. Cosa vorresti sapere?"

FOR GREETINGS:
- For casual greetings (ciao, salve, buongiorno) → respond naturally and ask how you can help

{settings.language_config}"""
        }],
        functions=[
            # ========================================
            # ❌ BOOKING DISABLED
            # ========================================
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
                description="Route to info agent for ALL requests - questions about services, prices, clinic hours, exam requirements, documents, or any healthcare-related questions. Also use this when user wants to book (booking not available, offer info instead).",
                properties={
                    "user_query": {
                        "type": "string",
                        "description": "The user's question or request (e.g., 'Quanto costa un esame del sangue?', 'Vorrei prenotare' → explain booking unavailable then ask what info they need)"
                    }
                },
                required=["user_query"]
            )
        ],
        respond_immediately=True  # Bot speaks first
    )
