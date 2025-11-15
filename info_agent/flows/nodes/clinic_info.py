"""
Clinic Info Flow Nodes
CRITICAL: ALWAYS collects location first per client requirement
Client explicitly states: "ALWAYS ask for the location where you want to know this information"
"""

from pipecat_flows import NodeConfig, FlowsFunctionSchema
from info_agent.config.settings import info_settings


def create_collect_location_node() -> NodeConfig:
    """
    CRITICAL NODE: Always ask for location first
    Client requirement: "When requesting Summer Closures or Blood Collection Times,
    ALWAYS ask for the location where you want to know this information"
    
    Example from client:
    Patient: "Hi, are you having summer closures?"
    Ualà: "Hi, could you tell me which location you would like to know
           if there are any summer closures?"
    Patient: "Novara"
    """
    from info_agent.flows.handlers.clinic_handlers import record_location_handler
    
    return NodeConfig(
        name="collect_location",
        task_messages=[
            {
                "role": "system",
                "content": f"Ask the patient which location/city they want information about in {info_settings.agent_config['language']}. Examples: Novara, Biella, Milano, Torino."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="record_location",
                handler=record_location_handler,
                description="Record the clinic location for information query",
                properties={
                    "location": {
                        "type": "string",
                        "description": "City or location name (e.g., Novara, Biella, Milano)"
                    }
                },
                required=["location"]
            )
        ]
    )


def create_clinic_info_result_node() -> NodeConfig:
    """
    Call clinic info API with location + info_type from flow state
    The info_type was captured in initial_details by intent handler
    """
    from info_agent.flows.handlers.clinic_handlers import get_clinic_info_final_handler
    
    return NodeConfig(
        name="clinic_info_result",
        task_messages=[
            {
                "role": "system",
                "content": "Acknowledge that you're checking the clinic information now."
            }
        ],
        pre_actions=[
            {
                "type": "tts_say",
                "text": "Un momento, controllo le informazioni per te..."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="get_clinic_info_final",
                handler=get_clinic_info_final_handler,
                description="Get clinic information with location and info type from state",
                properties={},  # Uses flow_manager.state
                required=[]
            )
        ]
    )
