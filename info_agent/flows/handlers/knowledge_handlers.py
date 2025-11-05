"""
Knowledge Base Handlers
Handles knowledge base queries and FAQ responses
"""

from typing import Tuple, Dict, Any
from loguru import logger

from pipecat_flows import FlowManager, NodeConfig, FlowArgs


async def query_knowledge_base_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Query knowledge base and transition to answer node
    
    Args:
        args: Function arguments containing query
        flow_manager: Flow manager instance
        
    Returns:
        Tuple of (result dict, next node)
    """
    try:
        query = args.get("query", "").strip()
        
        if not query:
            logger.warning("⚠️ Empty query received")
            return {
                "success": False,
                "answer": "Per favore, ripeti la tua domanda.",
                "confidence": 0.0
            }, None  # Stay in current node
        
        logger.info(f"📚 Knowledge base query: '{query[:100]}...'")
        
        # Query knowledge base service
        from info_agent.services.knowledge_base import knowledge_base_service
        result = await knowledge_base_service.query(query)
        
        # Store query and answer in flow state
        flow_manager.state["last_query"] = query
        flow_manager.state["last_answer"] = result.answer
        flow_manager.state["last_confidence"] = result.confidence
        
        if result.success:
            logger.success(f"✅ Knowledge base answered query (confidence: {result.confidence:.2f})")
            
            # Return to answer node to check for follow-up
            from info_agent.flows.nodes.answer import create_answer_node
            return {
                "success": True,
                "answer": result.answer,
                "confidence": result.confidence,
                "source": result.source
            }, create_answer_node()
        else:
            # API failed - offer transfer
            logger.error(f"❌ Knowledge base query failed: {result.error}")
            
            from info_agent.flows.nodes.transfer import create_transfer_node
            return {
                "success": False,
                "answer": result.answer,
                "error": result.error
            }, create_transfer_node()
            
    except Exception as e:
        logger.error(f"❌ Knowledge base handler error: {e}")
        
        # On error, offer transfer
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {
            "success": False,
            "error": str(e),
            "answer": "Mi dispiace, ho riscontrato un problema. Ti trasferisco a un collega."
        }, create_transfer_node()