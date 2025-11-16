"""
Flow Manager
Initializes and manages conversation flows for info agent
"""

from pipecat_flows import FlowManager, ContextStrategy, ContextStrategyConfig
from pipecat.pipeline.task import PipelineTask
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.transports.websocket.fastapi import FastAPIWebsocketTransport
from loguru import logger


def create_flow_manager(
    task: PipelineTask,
    llm: OpenAILLMService,
    context_aggregator: OpenAILLMContext,
    transport: FastAPIWebsocketTransport
) -> FlowManager:
    """
    Create FlowManager for info agent with appropriate context strategy
    
    Context Strategy: RESET_WITH_SUMMARY
    - For multi-query info agents, prevents context overflow
    - Keeps important information while managing token usage
    - Pipecat recommendation for info/FAQ agents
    
    Args:
        task: Pipeline task instance
        llm: LLM service instance
        context_aggregator: Context aggregator instance
        transport: Transport instance
        
    Returns:
        Configured FlowManager instance
    """
    logger.info("🔄 Creating FlowManager for Info Agent")
    
    flow_manager = FlowManager(
        task=task,
        llm=llm,
        context_aggregator=context_aggregator,
        transport=transport,
        context_strategy=ContextStrategyConfig(
            strategy=ContextStrategy.RESET_WITH_SUMMARY,
            summary_prompt="Summarize the key information provided to the patient and any parameters collected so far."
        )
    )
    
    logger.success("✅ FlowManager created with RESET_WITH_SUMMARY context strategy")
    return flow_manager


async def initialize_flow_manager(
    flow_manager: FlowManager,
    start_node: str = "greeting"
) -> None:
    """
    Initialize flow manager with specified starting node
    
    Args:
        flow_manager: FlowManager instance
        start_node: Name of starting node (default: "greeting")
    """
    logger.info(f"🎯 Initializing FlowManager with start node: {start_node}")
    
    if start_node == "greeting":
        # Default: Start with greeting node
        from info_agent.flows.nodes.greeting import create_greeting_node
        await flow_manager.initialize(create_greeting_node())
        logger.success("✅ Flow initialized with greeting node")
        
    else:
        
        logger.warning(f"⚠️ Unknown start node '{start_node}', defaulting to greeting")
        from info_agent.flows.nodes.greeting import create_greeting_node
        await flow_manager.initialize(create_greeting_node())
        logger.success("✅ Flow initialized with greeting node (default)")
