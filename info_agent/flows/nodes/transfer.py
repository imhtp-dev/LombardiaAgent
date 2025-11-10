"""
Transfer Node
Handles transfer to human operator
"""

from pipecat_flows import NodeConfig
from info_agent.config.settings import info_settings


def create_transfer_node() -> NodeConfig:
    """
    Create transfer node that handles escalation to human operator
    This node confirms transfer and ends the conversation
    """
    
    return NodeConfig(
        name="transfer",
        task_messages=[
            {
                "role": "system",
                "content": f"Inform the user that you are transferring them to a human colleague who will be able to assist them. Thank them for their patience. {info_settings.agent_config['language']} is required."
            }
        ],
        functions=[],  # No functions needed, just inform and transfer
        post_actions=[
            {
                "type": "end_conversation",
                "text": "Sto trasferendo la chiamata a un collega. Grazie per la pazienza."
            }
        ]
    )