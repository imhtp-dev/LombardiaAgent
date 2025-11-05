"""
Pricing Handlers
Handles competitive and non-competitive visit pricing queries
"""

from typing import Tuple, Dict, Any
from loguru import logger

from pipecat_flows import FlowManager, NodeConfig, FlowArgs


async def get_competitive_price_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Get competitive (agonistic) visit price
    Requires: age, gender, sport, region
    
    Args:
        args: Function arguments with age, gender, sport, region
        flow_manager: Flow manager instance
        
    Returns:
        Tuple of (result dict, next node)
    """
    try:
        # Extract parameters
        age = args.get("age")
        gender = args.get("gender", "").upper()
        sport = args.get("sport", "").strip()
        region = args.get("region", "").strip()
        
        # Validate parameters
        if not all([age, gender, sport, region]):
            logger.warning("⚠️ Missing parameters for competitive price")
            return {
                "success": False,
                "error": "Missing required parameters"
            }, None  # Stay in current node
        
        if gender not in ["M", "F"]:
            logger.warning(f"⚠️ Invalid gender: {gender}")
            return {
                "success": False,
                "error": "Gender must be M or F"
            }, None
        
        logger.info(f"💰 Getting competitive price: age={age}, gender={gender}, sport={sport}, region={region}")
        
        # Query pricing service
        from info_agent.services.pricing_service import pricing_service
        result = await pricing_service.get_competitive_price(
            age=age,
            gender=gender,
            sport=sport,
            region=region
        )
        
        # Store in flow state
        flow_manager.state["last_price_query"] = {
            "type": "competitive",
            "price": result.price,
            "visit_type": result.visit_type,
            "parameters": {
                "age": age,
                "gender": gender,
                "sport": sport,
                "region": region
            }
        }
        
        if result.success:
            logger.success(f"✅ Competitive price: €{result.price}")
            
            # Return to answer node
            from info_agent.flows.nodes.answer import create_answer_node
            return {
                "success": True,
                "price": result.price,
                "visit_type": result.visit_type,
                "currency": result.currency
            }, create_answer_node()
        else:
            # API failed - offer transfer
            logger.error(f"❌ Pricing API failed: {result.error}")
            
            from info_agent.flows.nodes.transfer import create_transfer_node
            return {
                "success": False,
                "error": result.error
            }, create_transfer_node()
            
    except Exception as e:
        logger.error(f"❌ Competitive price handler error: {e}")
        
        # On error, offer transfer
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {
            "success": False,
            "error": str(e)
        }, create_transfer_node()


async def get_non_competitive_price_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Get non-competitive (non-agonistic) visit price
    Requires: ecg_under_stress (boolean)
    
    Args:
        args: Function arguments with ecg_under_stress
        flow_manager: Flow manager instance
        
    Returns:
        Tuple of (result dict, next node)
    """
    try:
        # Extract parameter
        ecg_under_stress = args.get("ecg_under_stress")
        
        if ecg_under_stress is None:
            logger.warning("⚠️ Missing ecg_under_stress parameter")
            return {
                "success": False,
                "error": "Missing ecg_under_stress parameter"
            }, None
        
        logger.info(f"💰 Getting non-competitive price: ECG under stress={ecg_under_stress}")
        
        # Query pricing service
        from info_agent.services.pricing_service import pricing_service
        result = await pricing_service.get_non_competitive_price(
            ecg_under_stress=ecg_under_stress
        )
        
        # Store in flow state
        flow_manager.state["last_price_query"] = {
            "type": "non_competitive",
            "price": result.price,
            "visit_type": result.visit_type,
            "parameters": {
                "ecg_under_stress": ecg_under_stress
            }
        }
        
        if result.success:
            logger.success(f"✅ Non-competitive price: €{result.price}")
            
            # Return to answer node
            from info_agent.flows.nodes.answer import create_answer_node
            return {
                "success": True,
                "price": result.price,
                "visit_type": result.visit_type,
                "currency": result.currency
            }, create_answer_node()
        else:
            # API failed - offer transfer
            logger.error(f"❌ Pricing API failed: {result.error}")
            
            from info_agent.flows.nodes.transfer import create_transfer_node
            return {
                "success": False,
                "error": result.error
            }, create_transfer_node()
            
    except Exception as e:
        logger.error(f"❌ Non-competitive price handler error: {e}")
        
        # On error, offer transfer
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {
            "success": False,
            "error": str(e)
        }, create_transfer_node()