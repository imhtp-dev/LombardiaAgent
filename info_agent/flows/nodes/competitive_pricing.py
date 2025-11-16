"""
Competitive Pricing Flow Nodes
Step-by-step parameter collection following client requirement:
"Ask ONE question at a time - Never pile up requests"
"""

from pipecat_flows import NodeConfig, FlowsFunctionSchema
from info_agent.config.settings import info_settings


def create_collect_age_node() -> NodeConfig:
    """
    Step 1: Collect patient age - ONLY age, nothing else
    Following Pipecat principle: "One task per node"
    """
    from info_agent.flows.handlers.pricing_handlers import record_age_handler
    
    return NodeConfig(
        name="collect_age",
        task_messages=[
            {
                "role": "system",
                "content": f"Ask the patient for their age in years. Keep it short and friendly in {info_settings.agent_config['language']}."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="record_age",
                handler=record_age_handler,
                description="Record the patient's age",
                properties={
                    "age": {
                        "type": "integer",
                        "description": "Patient age in years"
                    }
                },
                required=["age"]
            )
        ]
    )


def create_collect_gender_node() -> NodeConfig:
    """
    Step 2: Collect patient gender - ONLY gender
    """
    from info_agent.flows.handlers.pricing_handlers import record_gender_handler
    
    return NodeConfig(
        name="collect_gender",
        task_messages=[
            {
                "role": "system",
                "content": f"Ask if the patient is male (maschio) or female (femmina) in {info_settings.agent_config['language']}. Keep it brief."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="record_gender",
                handler=record_gender_handler,
                description="Record patient gender",
                properties={
                    "gender": {
                        "type": "string",
                        "enum": ["M", "F"],
                        "description": "M for male (maschio), F for female (femmina)"
                    }
                },
                required=["gender"]
            )
        ]
    )


def create_collect_sport_node() -> NodeConfig:
    """
    Step 3: Collect sport practiced - ONLY sport
    """
    from info_agent.flows.handlers.pricing_handlers import record_sport_handler
    
    return NodeConfig(
        name="collect_sport",
        task_messages=[
            {
                "role": "system",
                "content": f"Ask which sport the patient practices in {info_settings.agent_config['language']}. Examples: calcio, basket, nuoto, pallavolo."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="record_sport",
                handler=record_sport_handler,
                description="Record the sport practiced",
                properties={
                    "sport": {
                        "type": "string",
                        "description": "Sport name in Italian (e.g., calcio, basket, nuoto)"
                    }
                },
                required=["sport"]
            )
        ]
    )


def create_collect_region_node() -> NodeConfig:
    """
    Step 4: Collect region - ONLY region
    """
    from info_agent.flows.handlers.pricing_handlers import record_region_handler
    
    return NodeConfig(
        name="collect_region",
        task_messages=[
            {
                "role": "system",
                "content": f"Ask in which Italian region they want to do the visit in {info_settings.agent_config['language']}. Examples: Piemonte, Lombardia, Lazio."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="record_region",
                handler=record_region_handler,
                description="Record the region for the visit",
                properties={
                    "region": {
                        "type": "string",
                        "description": "Italian region name (e.g., Piemonte, Lombardia)"
                    }
                },
                required=["region"]
            )
        ]
    )


def create_competitive_price_result_node() -> NodeConfig:
    """
    Step 5: Call pricing API with all collected parameters
    All parameters stored in flow_manager.state by previous nodes
    """
    from info_agent.flows.handlers.pricing_handlers import get_competitive_price_final_handler
    
    return NodeConfig(
        name="competitive_price_result",
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
                name="get_final_price",
                handler=get_competitive_price_final_handler,
                description="Get the competitive visit price with all collected parameters from state",
                properties={},  # No properties - uses flow_manager.state
                required=[]
            )
        ]
    )
