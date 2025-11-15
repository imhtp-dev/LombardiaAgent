"""
Exam List Flow Nodes
Can query exams by visit type OR by sport
"""

from pipecat_flows import NodeConfig, FlowsFunctionSchema
from info_agent.config.settings import info_settings


def create_exam_list_choice_node() -> NodeConfig:
    """
    Determine if user wants exams by visit type or by sport
    """
    from info_agent.flows.handlers.exam_handlers import choose_exam_query_type_handler
    
    return NodeConfig(
        name="exam_list_choice",
        task_messages=[
            {
                "role": "system",
                "content": f"Ask if they want to know the exam list for a specific visit type (A1, A2, etc.) or for a specific sport in {info_settings.agent_config['language']}."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="choose_exam_query_type",
                handler=choose_exam_query_type_handler,
                description="Determine if querying by visit type or sport",
                properties={
                    "query_type": {
                        "type": "string",
                        "enum": ["by_visit_type", "by_sport"],
                        "description": "Whether to get exams by visit type or by sport"
                    }
                },
                required=["query_type"]
            )
        ]
    )


def create_collect_visit_type_node() -> NodeConfig:
    """
    Collect visit type (A1, A2, A3, B1, B2, B3, B4, B5)
    """
    from info_agent.flows.handlers.exam_handlers import record_visit_type_handler
    
    return NodeConfig(
        name="collect_visit_type",
        task_messages=[
            {
                "role": "system",
                "content": f"Ask for the visit type. Valid types are: A1, A2, A3, B1, B2, B3, B4, B5 in {info_settings.agent_config['language']}."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="record_visit_type",
                handler=record_visit_type_handler,
                description="Record the visit type",
                properties={
                    "visit_type": {
                        "type": "string",
                        "enum": ["A1", "A2", "A3", "B1", "B2", "B3", "B4", "B5"],
                        "description": "Sports medicine visit type"
                    }
                },
                required=["visit_type"]
            )
        ]
    )


def create_collect_sport_name_node() -> NodeConfig:
    """
    Collect sport name for exam list query
    """
    from info_agent.flows.handlers.exam_handlers import record_sport_name_handler
    
    return NodeConfig(
        name="collect_sport_name",
        task_messages=[
            {
                "role": "system",
                "content": f"Ask which sport they want to know the exam list for in {info_settings.agent_config['language']}. Examples: calcio, basket, nuoto."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="record_sport_name",
                handler=record_sport_name_handler,
                description="Record the sport name",
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


def create_exam_list_result_node() -> NodeConfig:
    """
    Call exam list API with collected parameters
    """
    from info_agent.flows.handlers.exam_handlers import get_exam_list_final_handler
    
    return NodeConfig(
        name="exam_list_result",
        task_messages=[
            {
                "role": "system",
                "content": "Acknowledge that you're checking the exam list now."
            }
        ],
        pre_actions=[
            {
                "type": "tts_say",
                "text": "Un momento, controllo gli esami richiesti..."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="get_exam_list_final",
                handler=get_exam_list_final_handler,
                description="Get the exam list with parameters from state",
                properties={},  # Uses flow_manager.state
                required=[]
            )
        ]
    )
