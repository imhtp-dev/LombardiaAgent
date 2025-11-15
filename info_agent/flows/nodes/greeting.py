"""
Greeting Node
Initial conversation node with all available information tools
"""

from pipecat_flows import NodeConfig, FlowsFunctionSchema
from info_agent.config.settings import info_settings


def create_greeting_node() -> NodeConfig:
    
    # Import handlers
    from info_agent.flows.handlers.knowledge_handlers import query_knowledge_base_handler
    from info_agent.flows.handlers.pricing_handlers import (
        get_competitive_price_handler,
        get_non_competitive_price_handler
    )
    from info_agent.flows.handlers.exam_handlers import (
        get_exams_by_visit_handler,
        get_exams_by_sport_handler
    )
    from info_agent.flows.handlers.clinic_handlers import get_clinic_info_handler
    from info_agent.flows.handlers.transfer_handlers import request_transfer_handler
    
    # Define all available functions
    functions = [
        # Knowledge Base - Most common, handles general FAQs
        FlowsFunctionSchema(
            name="query_knowledge_base",
            handler=query_knowledge_base_handler,
            description="Search Cerba Healthcare knowledge base for medical information, FAQs, documents, forms, exam preparations, and general questions. Use this for ANY medical or procedural questions.",
            properties={
                "query": {
                    "type": "string",
                    "description": "Natural language question to search the knowledge base"
                }
            },
            required=["query"]
        ),
        
        # Competitive Visit Pricing
        FlowsFunctionSchema(
            name="get_competitive_visit_price",
            handler=get_competitive_price_handler,
            description="Get price for competitive (agonistic) sports medicine visit. Requires age, gender, sport, and region. Ask for these parameters ONE AT A TIME.",
            properties={
                "age": {
                    "type": "integer",
                    "description": "Patient age in years"
                },
                "gender": {
                    "type": "string",
                    "enum": ["M", "F"],
                    "description": "Patient gender - M for Male (Maschio), F for Female (Femmina)"
                },
                "sport": {
                    "type": "string",
                    "description": "Sport practiced by the patient (in Italian, e.g., 'calcio', 'basket')"
                },
                "region": {
                    "type": "string",
                    "description": "Italian region where visit will be performed (e.g., 'Piemonte', 'Lombardia')"
                }
            },
            required=["age", "gender", "sport", "region"]
        ),
        
        # Non-Competitive Visit Pricing
        FlowsFunctionSchema(
            name="get_non_competitive_visit_price",
            handler=get_non_competitive_price_handler,
            description="Get price for non-competitive (non-agonistic) sports medicine visit. Only needs to know if ECG under stress is required.",
            properties={
                "ecg_under_stress": {
                    "type": "boolean",
                    "description": "Whether ECG under stress is needed (True) or standard ECG (False)"
                }
            },
            required=["ecg_under_stress"]
        ),
        
        # Exam List by Visit Type
        FlowsFunctionSchema(
            name="get_exam_list_by_visit_type",
            handler=get_exams_by_visit_handler,
            description="Get list of examinations required for a specific visit type. Visit types are: A1, A2, A3, B1, B2, B3, B4, B5.",
            properties={
                "visit_type": {
                    "type": "string",
                    "enum": ["A1", "A2", "A3", "B1", "B2", "B3", "B4", "B5"],
                    "description": "Type of sports medicine visit"
                }
            },
            required=["visit_type"]
        ),
        
        # Exam List by Sport
        FlowsFunctionSchema(
            name="get_exam_list_by_sport",
            handler=get_exams_by_sport_handler,
            description="Get list of examinations required for a specific sport.",
            properties={
                "sport": {
                    "type": "string",
                    "description": "Name of the sport in Italian (e.g., 'calcio', 'basket', 'nuoto')"
                }
            },
            required=["sport"]
        ),
        
        # Clinic Information
        FlowsFunctionSchema(
            name="get_clinic_info",
            handler=get_clinic_info_handler,
            description="Get information about clinic hours, locations, summer closures, blood collection times. ALWAYS ask for the location first before calling this function.",
            properties={
                "location": {
                    "type": "string",
                    "description": "Clinic location/city (e.g., 'Novara', 'Biella', 'Milano')"
                },
                "info_type": {
                    "type": "string",
                    "description": "Type of information requested (e.g., 'summer closures', 'blood collection times', 'opening hours')"
                }
            },
            required=["location", "info_type"]
        ),
        
        # Transfer to Human
        FlowsFunctionSchema(
            name="request_transfer",
            handler=request_transfer_handler,
            description="Transfer the call to a human operator. Use when: (1) user wants to book appointment, (2) cannot find satisfactory answer, (3) user explicitly requests transfer, (4) SSN/Agreement questions.",
            properties={
                "reason": {
                    "type": "string",
                    "description": "Reason for transfer (e.g., 'booking request', 'cannot answer question', 'user request', 'SSN inquiry')"
                }
            },
            required=["reason"]
        ),
    ]
    
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
                "content": f"Listen to the caller's question and ALWAYS use the appropriate function to answer. NEVER answer from your own knowledge. Greet if this is the first message, otherwise answer their question using tools. {info_settings.agent_config['language']} is required."
            }
        ],
        functions=functions,
        respond_immediately=False  # Don't greet automatically for API calls
    )
