from pipecat_flows import FlowManager
from pipecat.pipeline.task import PipelineTask
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.transports.daily.transport import DailyTransport

from flows.nodes.greeting import create_greeting_node


def create_flow_manager(
    task: PipelineTask,
    llm: OpenAILLMService,
    context_aggregator: OpenAILLMContext,
    transport: DailyTransport
) -> FlowManager:
    """Create and initialize FlowManager with greeting node"""
    
    # Initialize FlowManager for dynamic flows
    flow_manager = FlowManager(
        task=task,
        llm=llm,
        context_aggregator=context_aggregator,
        transport=transport
    )
    
    return flow_manager


async def initialize_flow_manager(flow_manager: FlowManager, start_node: str = "greeting") -> None:
    """Initialize flow manager with specified starting node"""
    if start_node == "email":
        # Create a special entry node that switches STT then goes to email collection
        from pipecat_flows import NodeConfig, FlowsFunctionSchema
        from flows.handlers.patient_detail_handlers import start_email_collection_with_stt_switch

        email_entry_node = NodeConfig(
            name="email_entry",
            role_messages=[{
                "role": "system",
                "content": "Switching to high-accuracy transcription for email collection."
            }],
            task_messages=[{
                "role": "system",
                "content": "I'm switching to high-accuracy mode for email collection. Please wait a moment."
            }],
            functions=[
                FlowsFunctionSchema(
                    name="start_email_collection",
                    handler=start_email_collection_with_stt_switch,
                    description="Initialize email collection with enhanced transcription",
                    properties={},
                    required=[]
                )
            ]
        )
        await flow_manager.initialize(email_entry_node)
    elif start_node == "phone":
        from flows.nodes.patient_details import create_collect_phone_node
        await flow_manager.initialize(create_collect_phone_node())
    elif start_node == "name":
        from flows.nodes.patient_details import create_collect_name_node
        await flow_manager.initialize(create_collect_name_node())
    elif start_node == "fiscal_code":
        from flows.nodes.patient_details import create_collect_fiscal_code_node
        await flow_manager.initialize(create_collect_fiscal_code_node())
    else:
        # Default to greeting node
        await flow_manager.initialize(create_greeting_node())