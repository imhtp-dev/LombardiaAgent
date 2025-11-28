"""
API Handlers - Consolidated
All 6 API tool handlers for one-shot agent architecture.
Each handler calls its respective API and returns to greeting node for follow-up.
Enhanced with function call tracking for analytics.
"""

from typing import Tuple, Dict, Any
from loguru import logger

from pipecat_flows import FlowManager, NodeConfig, FlowArgs
from info_agent.services.call_data_extractor import get_call_extractor


# ============================================================================
# 1. KNOWLEDGE BASE HANDLER
# ============================================================================

async def query_knowledge_base_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Query knowledge base for FAQs, documents, forms, preparation instructions.
    Returns to greeting node to allow follow-up questions.
    """
    try:
        query = args.get("query", "").strip()

        if not query:
            logger.warning("⚠️ Empty knowledge base query")
            from info_agent.flows.nodes.conversation import create_greeting_node
            return {
                "success": False,
                "error": "No query provided"
            }, create_greeting_node()

        logger.info(f"📚 Knowledge Base Query: {query[:100]}...")

        # Call knowledge base service
        from info_agent.services.knowledge_base import knowledge_base_service
        result = await knowledge_base_service.query(query)

        if result.success:
            logger.success(f"✅ Knowledge base answer retrieved (confidence: {result.confidence})")

            # Track function call for analytics
            session_id = flow_manager.state.get("session_id")
            if session_id:
                call_extractor = get_call_extractor(session_id)
                call_extractor.add_function_call(
                    function_name="query_knowledge_base",
                    parameters={"query": query},
                    result={"confidence": result.confidence, "source": result.source}
                )

            # Return to greeting node for follow-up
            from info_agent.flows.nodes.conversation import create_greeting_node
            return {
                "success": True,
                "query": query,
                "answer": result.answer,
                "confidence": result.confidence,
                "source": result.source
            }, create_greeting_node(flow_manager)
        else:
            logger.error(f"❌ Knowledge base query failed: {result.error}")

            # Offer transfer if no answer found
            from info_agent.flows.nodes.transfer import create_transfer_node
            return {
                "success": False,
                "error": result.error,
                "message": "Information not found in knowledge base"
            }, create_transfer_node()

    except Exception as e:
        logger.error(f"❌ Knowledge base handler error: {e}")
        import traceback
        traceback.print_exc()

        from info_agent.flows.nodes.transfer import create_transfer_node
        return {"success": False, "error": str(e)}, create_transfer_node()


# ============================================================================
# 2. COMPETITIVE (AGONISTIC) PRICING HANDLER
# ============================================================================

async def get_competitive_pricing_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Get agonistic visit pricing.
    Requires: age, gender, sport, region
    LLM will naturally collect these parameters through conversation.
    """
    try:
        age = args.get("age")
        gender = args.get("gender", "").strip().upper()
        sport = args.get("sport", "").strip()
        region = args.get("region", "").strip()

        # Validate all required parameters
        missing_params = []
        if not age:
            missing_params.append("age")
        if not gender:
            missing_params.append("gender")
        if not sport:
            missing_params.append("sport")
        if not region:
            missing_params.append("region")

        if missing_params:
            logger.warning(f"⚠️ Missing parameters for competitive pricing: {missing_params}")
            # Return to greeting - LLM will ask for missing params
            from info_agent.flows.nodes.conversation import create_greeting_node
            return {
                "success": False,
                "missing_params": missing_params,
                "message": "Missing required parameters for pricing calculation"
            }, create_greeting_node()

        logger.info(f"💰 Competitive Pricing Query:")
        logger.info(f"   Age: {age}, Gender: {gender}, Sport: {sport}, Region: {region}")

        # Call pricing service
        from info_agent.services.pricing_service import pricing_service
        result = await pricing_service.get_competitive_price(age, gender, sport, region)

        if result.success:
            logger.success(f"✅ Competitive price retrieved: €{result.price}")

            # Track function call for analytics
            session_id = flow_manager.state.get("session_id")
            if session_id:
                call_extractor = get_call_extractor(session_id)
                call_extractor.add_function_call(
                    function_name="get_competitive_pricing",
                    parameters={"age": age, "gender": gender, "sport": sport, "region": region},
                    result={"price": result.price, "visit_type": result.visit_type}
                )

            # Return to greeting node for follow-up
            from info_agent.flows.nodes.conversation import create_greeting_node
            return {
                "success": True,
                "price": result.price,
                "visit_type": result.visit_type,
                "age": age,
                "gender": gender,
                "sport": sport,
                "region": region
            }, create_greeting_node(flow_manager)
        else:
            logger.error(f"❌ Competitive pricing failed: {result.error}")

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
# 3. NON-COMPETITIVE (NON-AGONISTIC) PRICING HANDLER
# ============================================================================

async def get_non_competitive_pricing_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Get non-agonistic visit pricing.
    Requires: ecg_under_stress (boolean)
    """
    try:
        ecg_under_stress = args.get("ecg_under_stress")

        if ecg_under_stress is None:
            logger.warning("⚠️ Missing ECG preference for non-competitive pricing")
            # Return to greeting - LLM will ask
            from info_agent.flows.nodes.conversation import create_greeting_node
            return {
                "success": False,
                "missing_params": ["ecg_under_stress"],
                "message": "Need to know if ECG under stress is required"
            }, create_greeting_node()

        logger.info(f"💰 Non-Competitive Pricing Query: ECG under stress = {ecg_under_stress}")

        # Call pricing service
        from info_agent.services.pricing_service import pricing_service
        result = await pricing_service.get_non_competitive_price(ecg_under_stress)

        if result.success:
            logger.success(f"✅ Non-competitive price retrieved: €{result.price}")

            # Track function call for analytics
            session_id = flow_manager.state.get("session_id")
            if session_id:
                call_extractor = get_call_extractor(session_id)
                call_extractor.add_function_call(
                    function_name="get_non_competitive_pricing",
                    parameters={"ecg_under_stress": ecg_under_stress},
                    result={"price": result.price}
                )

            # Return to greeting node for follow-up
            from info_agent.flows.nodes.conversation import create_greeting_node
            return {
                "success": True,
                "price": result.price,
                "ecg_under_stress": ecg_under_stress
            }, create_greeting_node(flow_manager)
        else:
            logger.error(f"❌ Non-competitive pricing failed: {result.error}")

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
# 4. EXAM LIST BY VISIT TYPE HANDLER
# ============================================================================

async def get_exam_by_visit_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Get exam list for visit type code (A1, A2, A3, B1-B5).
    Requires: visit_type
    """
    try:
        visit_type = args.get("visit_type", "").strip().upper()

        if not visit_type:
            logger.warning("⚠️ Missing visit_type for exam list")
            from info_agent.flows.nodes.conversation import create_greeting_node
            return {
                "success": False,
                "missing_params": ["visit_type"],
                "message": "Need visit type code (A1, A2, A3, B1-B5)"
            }, create_greeting_node()

        logger.info(f"📋 Exam List by Visit Type: {visit_type}")

        # Call exam service
        from info_agent.services.exam_service import exam_service
        result = await exam_service.get_exams_by_visit_type(visit_type)

        if result.success:
            logger.success(f"✅ Exam list retrieved for {visit_type}: {len(result.exams)} exams")

            # Track function call for analytics
            session_id = flow_manager.state.get("session_id")
            if session_id:
                call_extractor = get_call_extractor(session_id)
                call_extractor.add_function_call(
                    function_name="get_exam_by_visit",
                    parameters={"visit_type": visit_type},
                    result={"exam_count": len(result.exams), "visit_code": result.visit_code}
                )

            # Return to greeting node with extracted fields
            from info_agent.flows.nodes.conversation import create_greeting_node
            return {
                "success": True,
                "visit_type": visit_type,
                "visit_code": result.visit_code,
                "exams": result.exams,
                "exam_count": len(result.exams)
            }, create_greeting_node(flow_manager)
        else:
            logger.error(f"❌ Exam list by visit failed: {result.error}")

            from info_agent.flows.nodes.transfer import create_transfer_node
            return {
                "success": False,
                "error": result.error
            }, create_transfer_node()

    except Exception as e:
        logger.error(f"❌ Exam by visit handler error: {e}")
        import traceback
        traceback.print_exc()

        from info_agent.flows.nodes.transfer import create_transfer_node
        return {"success": False, "error": str(e)}, create_transfer_node()


# ============================================================================
# 5. EXAM LIST BY SPORT HANDLER
# ============================================================================

async def get_exam_by_sport_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Get exam list for specific sport.
    Requires: sport
    """
    try:
        sport = args.get("sport", "").strip()

        if not sport:
            logger.warning("⚠️ Missing sport for exam list")
            from info_agent.flows.nodes.conversation import create_greeting_node
            return {
                "success": False,
                "missing_params": ["sport"],
                "message": "Need sport name to get exam list"
            }, create_greeting_node()

        logger.info(f"📋 Exam List by Sport: {sport}")

        # Call exam service
        from info_agent.services.exam_service import exam_service
        result = await exam_service.get_exams_by_sport(sport)

        if result.success:
            logger.success(f"✅ Exam list retrieved for {sport}: {len(result.exams)} exams")

            # Track function call for analytics
            session_id = flow_manager.state.get("session_id")
            if session_id:
                call_extractor = get_call_extractor(session_id)
                call_extractor.add_function_call(
                    function_name="get_exam_by_sport",
                    parameters={"sport": sport},
                    result={"exam_count": len(result.exams), "visit_code": result.visit_code}
                )

            # Return to greeting node with extracted fields
            from info_agent.flows.nodes.conversation import create_greeting_node
            return {
                "success": True,
                "sport": sport,
                "visit_code": result.visit_code,
                "exams": result.exams,
                "exam_count": len(result.exams)
            }, create_greeting_node(flow_manager)
        else:
            logger.error(f"❌ Exam list by sport failed: {result.error}")

            from info_agent.flows.nodes.transfer import create_transfer_node
            return {
                "success": False,
                "error": result.error
            }, create_transfer_node()

    except Exception as e:
        logger.error(f"❌ Exam by sport handler error: {e}")
        import traceback
        traceback.print_exc()

        from info_agent.flows.nodes.transfer import create_transfer_node
        return {"success": False, "error": str(e)}, create_transfer_node()


# ============================================================================
# 6. CLINIC INFO HANDLER
# ============================================================================

async def get_clinic_info_handler(
    args: FlowArgs,
    flow_manager: FlowManager
) -> Tuple[Dict[str, Any], NodeConfig]:
    """
    Get clinic information (hours, closures, blood collection times).
    Requires: query (natural language including location)

    Natural language approach - LLM passes complete query directly to API.
    """
    try:
        query = args.get("query", "").strip()

        if not query:
            logger.warning("⚠️ Missing query for clinic info")
            # Return to greeting - LLM will ask
            from info_agent.flows.nodes.conversation import create_greeting_node
            return {
                "success": False,
                "missing_params": ["query"],
                "message": "Need query for clinic information"
            }, create_greeting_node()

        logger.info(f"🏥 Clinic Info Query: {query}")

        # Call clinic info service with natural language query
        from info_agent.services.clinic_info_service import clinic_info_service
        result = await clinic_info_service.get_clinic_info(query)

        if result.success:
            logger.success(f"✅ Clinic info retrieved")

            # Track function call for analytics
            session_id = flow_manager.state.get("session_id")
            if session_id:
                call_extractor = get_call_extractor(session_id)
                call_extractor.add_function_call(
                    function_name="get_clinic_info",
                    parameters={"query": query},
                    result={"success": True}
                )

            # Return to greeting node for follow-up
            from info_agent.flows.nodes.conversation import create_greeting_node
            return {
                "success": True,
                "query": query,
                "answer": result.answer
            }, create_greeting_node(flow_manager)
        else:
            logger.error(f"❌ Clinic info failed: {result.error}")

            from info_agent.flows.nodes.transfer import create_transfer_node
            return {
                "success": False,
                "error": result.error
            }, create_transfer_node()

    except Exception as e:
        logger.error(f"❌ Clinic info handler error: {e}")
        import traceback
        traceback.print_exc()

        from info_agent.flows.nodes.transfer import create_transfer_node
        return {"success": False, "error": str(e)}, create_transfer_node()
