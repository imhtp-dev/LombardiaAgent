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
    elif start_node == "slot_selection":
        from flows.nodes.booking import create_collect_datetime_node
        from models.requests import HealthService, HealthCenter

        # Pre-populate state with data from logs for testing
        # This simulates having gone through: service selection, center selection, patient info, etc.
        service = HealthService(
            uuid="9a93d65f-396a-45e4-9284-94481bdd2b51",
            name="RX Caviglia Destra ",
            code="RRAD0019",
            synonyms=["Esame Radiografico Caviglia Destra","Esame Radiografico Caviglia dx","Lastra Caviglia Destra","Radiografia Caviglia Destra","Radiografia Caviglia dx","Radiografia della Caviglia Destra","Raggi Caviglia Destra","Raggi Caviglia dx","Raggi x Caviglia Destra","Raggi x Caviglia dx","RX Caviglia dx","RX della Caviglia Destra"]
        )

        flow_manager.state.update({
            # Service selection data (from logs) - booking logic expects PLURAL
            "selected_service": service,  # Keep singular for compatibility
            "selected_services": [service],  # Add plural for booking logic
            # Center selection data (from logs)
            "selected_center": HealthCenter(
                uuid="6cff89d8-1f40-4eb8-bed7-f36e94a3355c",
                name="Rozzano Viale Toscana 35/37 - Delta Medica",
                address="Viale Toscana 35/37",
                city="Rozzano",
                district="Milano",
                phone="+39 02 1234567",
                region="Lombardia"
            ),
            # Patient data (from logs)
            "patient_data": {
                "gender": "m",
                "date_of_birth": "2007-04-27",
                "address": "Milan",
                "birth_city": "Milan"
            },
            # Cerba membership (from logs)
            "is_cerba_member": False
        })

        print("🧪 DATE SELECTION TEST MODE")
        print("=" * 50)
        print("📋 Pre-populated test data:")
        print(f"   Service: {flow_manager.state['selected_service'].name}")
        print(f"   Services (array): {[s.name for s in flow_manager.state['selected_services']]}")
        print(f"   Center: {flow_manager.state['selected_center'].name}")
        print(f"   Patient: Male, DOB: {flow_manager.state['patient_data']['date_of_birth']}")
        print("   📅 Starting from: Date selection")
        print("=" * 50)

        # Initialize with date collection node - user will be asked for preferred date/time
        await flow_manager.initialize(create_collect_datetime_node())
    else:
        # Default to greeting node
        await flow_manager.initialize(create_greeting_node())