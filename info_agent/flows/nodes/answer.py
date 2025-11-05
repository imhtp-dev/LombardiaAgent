"""
Answer Node
Handles follow-up after providing information to user
"""

from pipecat_flows import NodeConfig, FlowsFunctionSchema
from info_agent.config.settings import info_settings


def create_answer_node() -> NodeConfig:
    """
    Create answer node that checks if user needs more help
    After providing any answer, ask if user needs more information
    """
    
    # Import handlers
    from info_agent.flows.handlers.transfer_handlers import (
        check_followup_handler,
        request_transfer_handler
    )
    
    return NodeConfig(
        name="answer",
        task_messages=[
            {
                "role": "system",
                "content": f"You have just provided information to the user. Now politely ask if they need any other information or assistance. {info_settings.agent_config['language']} is required."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="check_followup",
                handler=check_followup_handler,
                description="Check if user needs more information or wants to end the conversation",
                properties={
                    "needs_more_help": {
                        "type": "boolean",
                        "description": "True if user needs more information, False if they are satisfied and want to end"
                    }
                },
                required=["needs_more_help"]
            ),
            FlowsFunctionSchema(
                name="request_transfer",
                handler=request_transfer_handler,
                description="Transfer to human operator if user requests it",
                properties={
                    "reason": {
                        "type": "string",
                        "description": "Reason for transfer"
                    }
                },
                required=["reason"]
            ),
        ]
    )


def create_goodbye_node() -> NodeConfig:
    """
    Create goodbye node for ending conversation
    """
    return NodeConfig(
        name="goodbye",
        task_messages=[
            {
                "role": "system",
                "content": f"Thank the user warmly for contacting Cerba Healthcare and wish them a good day. Say goodbye. {info_settings.agent_config['language']} is required."
            }
        ],
        functions=[],  # No functions, just goodbye message
        post_actions=[
            {
                "type": "end_conversation"
            }
        ]
    )