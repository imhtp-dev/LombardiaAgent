"""
Non-Competitive Pricing Flow Nodes
Simpler flow - only needs ECG preference
"""

from pipecat_flows import NodeConfig, FlowsFunctionSchema
from info_agent.config.settings import info_settings


def create_collect_ecg_preference_node() -> NodeConfig:
    """
    Ask if ECG under stress is needed
    Only parameter for non-competitive pricing
    """
    from info_agent.flows.handlers.pricing_handlers import record_ecg_preference_handler
    
    return NodeConfig(
        name="collect_ecg_preference",
        task_messages=[
            {
                "role": "system",
                "content": f"Ask if the patient needs an ECG under stress (ECG sotto sforzo) or standard ECG in {info_settings.agent_config['language']}. Keep it brief and friendly."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="record_ecg_preference",
                handler=record_ecg_preference_handler,
                description="Record whether ECG under stress is needed",
                properties={
                    "ecg_under_stress": {
                        "type": "boolean",
                        "description": "True if ECG under stress is needed, False for standard ECG"
                    }
                },
                required=["ecg_under_stress"]
            )
        ]
    )


def create_non_competitive_price_result_node() -> NodeConfig:
    """
    Call non-competitive pricing API with ECG preference from state
    """
    from info_agent.flows.handlers.pricing_handlers import get_non_competitive_price_final_handler
    
    return NodeConfig(
        name="non_competitive_price_result",
        task_messages=[
            {
                "role": "system",
                "content": "Acknowledge that you're checking the price now."
            }
        ],
        pre_actions=[
            {
                "type": "tts_say",
                "text": "Un momento, controllo il prezzo per te..."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="get_non_competitive_price_final",
                handler=get_non_competitive_price_final_handler,
                description="Get the non-competitive visit price with ECG preference from state",
                properties={},  # Uses flow_manager.state
                required=[]
            )
        ]
    )
