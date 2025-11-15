"""
Pricing Handlers - Step by Step Parameter Collection
Following client requirement: "Ask ONE question at a time"
Uses flow_manager.state to build up parameters across nodes
"""

from typing import Tuple, Dict, Any
from loguru import logger

from pipecat_flows import FlowManager, NodeConfig, FlowArgs


# ============================================================================
# COMPETITIVE PRICING FLOW - Step by Step Collection
# ============================================================================

async def record_age_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Step 1/4: Record age and move to gender collection
    """
    try:
        age = args.get("age")
        
        logger.info(f"📝 Competitive pricing - Recorded age: {age}")
        flow_manager.state["competitive_pricing_age"] = age
        
        # Move to gender collection
        from info_agent.flows.nodes.competitive_pricing import create_collect_gender_node
        return {"age": age, "step": "1/4"}, create_collect_gender_node()
        
    except Exception as e:
        logger.error(f"❌ Error recording age: {e}")
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {"success": False, "error": str(e)}, create_transfer_node()


async def record_gender_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Step 2/4: Record gender and move to sport collection
    """
    try:
        gender = args.get("gender")
        
        logger.info(f"📝 Competitive pricing - Recorded gender: {gender}")
        flow_manager.state["competitive_pricing_gender"] = gender
        
        # Move to sport collection
        from info_agent.flows.nodes.competitive_pricing import create_collect_sport_node
        return {"gender": gender, "step": "2/4"}, create_collect_sport_node()
        
    except Exception as e:
        logger.error(f"❌ Error recording gender: {e}")
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {"success": False, "error": str(e)}, create_transfer_node()


async def record_sport_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Step 3/4: Record sport and move to region collection
    """
    try:
        sport = args.get("sport")
        
        logger.info(f"📝 Competitive pricing - Recorded sport: {sport}")
        flow_manager.state["competitive_pricing_sport"] = sport
        
        # Move to region collection
        from info_agent.flows.nodes.competitive_pricing import create_collect_region_node
        return {"sport": sport, "step": "3/4"}, create_collect_region_node()
        
    except Exception as e:
        logger.error(f"❌ Error recording sport: {e}")
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {"success": False, "error": str(e)}, create_transfer_node()


async def record_region_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Step 4/4: Record region and move to API call
    All parameters now collected
    """
    try:
        region = args.get("region")
        
        logger.info(f"📝 Competitive pricing - Recorded region: {region}")
        flow_manager.state["competitive_pricing_region"] = region
        
        # All parameters collected - move to API call
        logger.success("✅ All competitive pricing parameters collected")
        from info_agent.flows.nodes.competitive_pricing import create_competitive_price_result_node
        return {"region": region, "step": "4/4"}, create_competitive_price_result_node()
        
    except Exception as e:
        logger.error(f"❌ Error recording region: {e}")
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {"success": False, "error": str(e)}, create_transfer_node()


async def get_competitive_price_final_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Final step: Call pricing API with all collected parameters from state
    """
    try:
        # Get all parameters from flow state
        age = flow_manager.state.get("competitive_pricing_age")
        gender = flow_manager.state.get("competitive_pricing_gender")
        sport = flow_manager.state.get("competitive_pricing_sport")
        region = flow_manager.state.get("competitive_pricing_region")
        
        logger.info(f"💰 Getting competitive price:")
        logger.info(f"   Age: {age}, Gender: {gender}")
        logger.info(f"   Sport: {sport}, Region: {region}")
        
        # Validate all parameters present
        if not all([age, gender, sport, region]):
            missing = []
            if not age: missing.append("age")
            if not gender: missing.append("gender")
            if not sport: missing.append("sport")
            if not region: missing.append("region")
            
            logger.error(f"❌ Missing parameters: {', '.join(missing)}")
            from info_agent.flows.nodes.transfer import create_transfer_node
            return {
                "success": False,
                "error": f"Missing parameters: {', '.join(missing)}"
            }, create_transfer_node()
        
        # Call pricing service
        from info_agent.services.pricing_service import pricing_service
        result = await pricing_service.get_competitive_price(
            age=age,
            gender=gender,
            sport=sport,
            region=region
        )
        
        if result.success:
            logger.success(f"✅ Competitive price retrieved: €{result.price}")
            
            # Clean up state for this flow
            flow_manager.state.pop("competitive_pricing_age", None)
            flow_manager.state.pop("competitive_pricing_gender", None)
            flow_manager.state.pop("competitive_pricing_sport", None)
            flow_manager.state.pop("competitive_pricing_region", None)
            
            # Move to answer node
            from info_agent.flows.nodes.answer import create_answer_node
            return {
                "success": True,
                "price": result.price,
                "details": result.details
            }, create_answer_node()
        else:
            logger.error(f"❌ Pricing API failed: {result.error}")
            
            # Offer transfer on API failure
            from info_agent.flows.nodes.transfer import create_transfer_node
            return {
                "success": False,
                "error": result.error
            }, create_transfer_node()
            
    except Exception as e:
        logger.error(f"❌ Competitive pricing handler error: {e}")
        import traceback
        traceback.print_exc()
        
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {"success": False, "error": str(e)}, create_transfer_node()


# ============================================================================
# NON-COMPETITIVE PRICING FLOW - Single Parameter
# ============================================================================

async def record_ecg_preference_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Record ECG preference and move to result node
    """
    try:
        ecg_under_stress = args.get("ecg_under_stress", False)
        
        logger.info(f"📝 Non-competitive pricing - ECG under stress: {ecg_under_stress}")
        flow_manager.state["non_competitive_ecg_under_stress"] = ecg_under_stress
        
        # Move to result node
        from info_agent.flows.nodes.non_competitive_pricing import create_non_competitive_price_result_node
        return {
            "ecg_under_stress": ecg_under_stress
        }, create_non_competitive_price_result_node()
        
    except Exception as e:
        logger.error(f"❌ Error recording ECG preference: {e}")
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {"success": False, "error": str(e)}, create_transfer_node()


async def get_non_competitive_price_final_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Call non-competitive pricing API
    """
    try:
        ecg_under_stress = flow_manager.state.get("non_competitive_ecg_under_stress", False)
        
        logger.info(f"💰 Getting non-competitive price (ECG under stress: {ecg_under_stress})")
        
        # Call pricing service
        from info_agent.services.pricing_service import pricing_service
        result = await pricing_service.get_non_competitive_price(
            ecg_under_stress=ecg_under_stress
        )
        
        if result.success:
            logger.success(f"✅ Non-competitive price retrieved: €{result.price}")
            
            # Clean up state
            flow_manager.state.pop("non_competitive_ecg_under_stress", None)
            
            # Move to answer node
            from info_agent.flows.nodes.answer import create_answer_node
            return {
                "success": True,
                "price": result.price,
                "details": result.details
            }, create_answer_node()
        else:
            logger.error(f"❌ Pricing API failed: {result.error}")
            
            from info_agent.flows.nodes.transfer import create_transfer_node
            return {
                "success": False,
                "error": result.error
            }, create_transfer_node()
            
    except Exception as e:
        logger.error(f"❌ Non-competitive pricing handler error: {e}")
        import traceback
        traceback.print_exc()
        
        from info_agent.flows.nodes.transfer import create_transfer_node
        return {"success": False, "error": str(e)}, create_transfer_node()


# ============================================================================
# LEGACY HANDLERS (kept for backward compatibility, but deprecated)
# ============================================================================

async def get_competitive_price_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    DEPRECATED: Old handler that expected all params at once
    Redirects to step-by-step flow
    """
    logger.warning("⚠️ DEPRECATED: get_competitive_price_handler called - redirecting to step-by-step flow")
    
    # Check if any parameters provided
    age = args.get("age")
    gender = args.get("gender")
    sport = args.get("sport")
    region = args.get("region")
    
    # Store any provided parameters
    if age:
        flow_manager.state["competitive_pricing_age"] = age
    if gender:
        flow_manager.state["competitive_pricing_gender"] = gender
    if sport:
        flow_manager.state["competitive_pricing_sport"] = sport
    if region:
        flow_manager.state["competitive_pricing_region"] = region
    
    # Determine next step based on what's missing
    from info_agent.flows.nodes.competitive_pricing import (
        create_collect_age_node,
        create_collect_gender_node,
        create_collect_sport_node,
        create_collect_region_node,
        create_competitive_price_result_node
    )
    
    if not age:
        return {"redirect": "collecting age"}, create_collect_age_node()
    elif not gender:
        return {"redirect": "collecting gender"}, create_collect_gender_node()
    elif not sport:
        return {"redirect": "collecting sport"}, create_collect_sport_node()
    elif not region:
        return {"redirect": "collecting region"}, create_collect_region_node()
    else:
        # All params provided - go to result
        return {"redirect": "all params provided"}, create_competitive_price_result_node()


async def get_non_competitive_price_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    DEPRECATED: Old handler - redirects to new flow
    """
    logger.warning("⚠️ DEPRECATED: get_non_competitive_price_handler called - redirecting to new flow")
    
    ecg_under_stress = args.get("ecg_under_stress")
    
    if ecg_under_stress is not None:
        flow_manager.state["non_competitive_ecg_under_stress"] = ecg_under_stress
        from info_agent.flows.nodes.non_competitive_pricing import create_non_competitive_price_result_node
        return {"redirect": "has ecg preference"}, create_non_competitive_price_result_node()
    else:
        from info_agent.flows.nodes.non_competitive_pricing import create_collect_ecg_preference_node
        return {"redirect": "collecting ecg preference"}, create_collect_ecg_preference_node()
