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

    Context Strategy: APPEND (changed from RESET_WITH_SUMMARY)
    - Maintains full conversation history for natural follow-up questions
    - One-shot agent benefits from continuous context
    - LLM can reference previous answers and provide better responses

    Args:
        task: Pipeline task instance
        llm: LLM service instance
        context_aggregator: Context aggregator instance
        transport: Transport instance

    Returns:
        Configured FlowManager instance
    """
    logger.info("🔄 Creating FlowManager for One-Shot Info Agent")

    flow_manager = FlowManager(
        task=task,
        llm=llm,
        context_aggregator=context_aggregator,
        transport=transport,
        context_strategy=ContextStrategyConfig(
            strategy=ContextStrategy.APPEND  # ✅ Keep full conversation context
        )
    )

    logger.success("✅ FlowManager created with APPEND context strategy (maintains conversation history)")
    return flow_manager


async def initialize_flow_manager(
    flow_manager: FlowManager,
    start_node: str = "greeting"
) -> None:
    """
    Initialize flow manager with specified starting node.

    Simplified one-shot agent architecture:
    - Only "greeting" node used (contains all 6 API tools)
    - LLM handles intent detection, parameter collection, API calls
    - Always starts with greeting node regardless of start_node parameter

    Args:
        flow_manager: FlowManager instance
        start_node: Name of starting node (always "greeting" in one-shot architecture)
    """
    logger.info(f"🎯 Initializing One-Shot Agent FlowManager")

    # One-shot architecture: Always start with greeting node
    # Greeting node contains ALL 6 API tools - LLM handles everything
    from info_agent.flows.nodes.greeting import create_greeting_node
    await flow_manager.initialize(create_greeting_node(flow_manager))  # ✅ Pass flow_manager for business_status
    logger.success("✅ One-shot agent flow initialized with greeting node (all 6 tools available)")
