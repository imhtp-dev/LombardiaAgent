"""
Greeting and initial conversation nodes
"""

from pipecat_flows import NodeConfig, FlowsFunctionSchema
from flows.handlers.service_handlers import search_health_services_and_transition
from config.settings import settings


def create_greeting_node() -> NodeConfig:
    """Create the initial greeting node"""
    return NodeConfig(
        name="greeting",
        role_messages=[{
            "role": "system",
            "content": f"You are Ualà, a calm and friendly virtual assistant (female voice) for Cerba Healthcare. Speak with warmth and clarity like a human, not like a robot. {settings.language_config}"
        }],
        task_messages=[{
            "role": "system",
            "content": f"Say: 'Hello, I'm Ualà, a virtual assistant for Cerba Healthcare. Can you tell me which service you would like to book?' When the user mentions ANY service name, immediately call search_health_services to search for it. {settings.language_config}"
        }],
        functions=[
            FlowsFunctionSchema(
                name="search_health_services",
                handler=search_health_services_and_transition,
                description="Search health services using fuzzy search",
                properties={
                    "search_term": {
                        "type": "string",
                        "description": "Name of the service to search for (e.g. 'cardiology', 'blood tests', 'ankle x-ray')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 3, maximum: 5)",
                        "default": 3,
                        "minimum": 1,
                        "maximum": 5
                    }
                },
                required=["search_term"]
            )
        ]
    )