"""
Transfer Node
Handles transfer to human operator with escalation API call
"""

from pipecat_flows import NodeConfig
from info_agent.config.settings import info_settings
from info_agent.flows.handlers.transfer_handlers import handle_transfer_escalation


def create_transfer_node() -> NodeConfig:
    """
    Create transfer node that handles escalation to human operator

    Flow:
    1. Agent says transfer message (Italian)
    2. Pre-action: Calls handle_transfer_escalation() which:
       - Runs early LLM analysis
       - Calls bridge escalation API
       - Stores analysis for Supabase
    3. Post-action: Ends conversation
    4. WebSocket closes automatically (handled by bridge)
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
        pre_actions=[handle_transfer_escalation],  # Call escalation API before ending
        post_actions=[
            {
                "type": "end_conversation",
                "text": "Attendi, ti sto trasferendo a un operatore umano."
            }
        ]
    )