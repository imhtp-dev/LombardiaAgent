"""
Knowledge Base Query Flow Node
For general questions, FAQs, documents, forms, etc.
"""

from pipecat_flows import NodeConfig, FlowsFunctionSchema
from info_agent.config.settings import info_settings


def create_knowledge_query_node() -> NodeConfig:
    """
    Query knowledge base for general information
    Most common flow - handles FAQs, documents, forms, preparations
    """
    from info_agent.flows.handlers.knowledge_handlers import query_knowledge_base_handler
    
    return NodeConfig(
        name="knowledge_query",
        task_messages=[
            {
                "role": "system",
                "content": f"The user has a general question. Ask them to clarify or provide more details if needed, then search the knowledge base in {info_settings.agent_config['language']}."
            }
        ],
        functions=[
            FlowsFunctionSchema(
                name="query_knowledge_base",
                handler=query_knowledge_base_handler,
                description="Search Cerba Healthcare knowledge base for medical information, FAQs, documents, forms, exam preparations, and general questions",
                properties={
                    "query": {
                        "type": "string",
                        "description": "Natural language question to search the knowledge base"
                    }
                },
                required=["query"]
            )
        ]
    )
