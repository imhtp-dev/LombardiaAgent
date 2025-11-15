"""
Greeting Node
Initial conversation - greets user and identifies their intent
Following Pipecat Flows best practice: ONE task per node
"""

from pipecat_flows import NodeConfig, FlowsFunctionSchema
from info_agent.config.settings import info_settings


def create_greeting_node() -> NodeConfig:
    """
    Initial greeting node - ONLY task is to greet and identify user intent
    Following client requirement: "Warmly greet the caller"
    Following Pipecat principle: "One task per node"
    """
    from info_agent.flows.handlers.intent_handlers import identify_intent_handler
    
    return NodeConfig(
        name="greeting",
        role_messages=[
            {
                "role": "system",
                "content": info_settings.system_prompt
            }
        ],
        task_messages=[
            {
                "role": "system",
                "content": f"Warmly greet the caller in {info_settings.agent_config['language']} and ask how you can help them today with Cerba Healthcare services. Keep it brief and friendly."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="identify_user_intent",
                handler=identify_intent_handler,
                description="Identify what type of information or service the user is requesting",
                properties={
                    "intent": {
                        "type": "string",
                        "enum": [
                            "general_question",
                            "competitive_pricing",
                            "non_competitive_pricing",
                            "clinic_info",
                            "exam_list",
                            "transfer_request"
                        ],
                        "description": "The category of information the user is seeking"
                    },
                    "initial_details": {
                        "type": "string",
                        "description": "Any specific details mentioned by the user (optional)"
                    }
                },
                required=["intent"]
            )
        ],
        respond_immediately=True  # ✅ Bot greets first when pipeline starts
    )
