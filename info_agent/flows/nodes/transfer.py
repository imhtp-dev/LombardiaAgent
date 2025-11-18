"""
Transfer Node
Handles transfer to human operator with escalation API call
"""

from pipecat_flows import NodeConfig
from info_agent.config.settings import info_settings


def create_transfer_node() -> NodeConfig:
    """
    Create transfer node that handles escalation to human operator

    Flow:
    1. request_transfer_handler calls handle_transfer_escalation() (runs LLM analysis + bridge API)
    2. Handler returns this transfer node
    3. Agent says transfer message (Italian)
    4. Post-action: Ends conversation
    5. WebSocket closes automatically (handled by bridge)
    """

    return NodeConfig(
        name="transfer",
        task_messages=[
            {
                "role": "system",
                "content": (
                    f"Say EXACTLY this message in Italian: "
                    f"'Attendi, ti sto trasferendo a un operatore umano.' "
                    f"{info_settings.agent_config['language']} is required."
                )
            }
        ],
        functions=[],  # No functions needed
        post_actions=[
            {
                "type": "end_conversation",
                "text": "Attendi, ti sto trasferendo a un operatore umano."
            }
        ]
    )