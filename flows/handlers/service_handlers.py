"""
Service search and selection flow handlers
"""

import json
from typing import Dict, Any, Tuple, List
from loguru import logger

from pipecat_flows import FlowManager, NodeConfig, FlowArgs
from services.fuzzy_search import fuzzy_search_service
from models.requests import HealthService


async def search_health_services_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Search for health services and dynamically create next node based on results"""
    try:
        search_term = args.get("search_term", "").strip()
        limit = min(args.get("limit", 3), 5)

        logger.info(f"🔍 Flow searching health services: '{search_term}' (limit: {limit})")

        # Store search parameters in flow state for the search node
        flow_manager.state["pending_search_term"] = search_term
        flow_manager.state["pending_search_limit"] = limit

        # Create intermediate node with pre_actions for immediate TTS
        search_status_text = f"Sto cercando servizi correlati a {search_term}. Attendi..."

        from flows.nodes.service_selection import create_search_processing_node
        return {
            "success": True,
            "message": f"Starting search for '{search_term}'"
        }, create_search_processing_node(search_term, limit, search_status_text)

    except Exception as e:
        logger.error(f"Flow service search initialization error: {e}")
        from flows.nodes.service_selection import create_search_retry_node
        return {
            "success": False,
            "message": "Service search failed. Please try again.",
            "services": []
        }, create_search_retry_node("Service search failed. Please try again.")


async def perform_health_services_search_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Perform the actual health services search after TTS message"""
    try:
        # Get stored search parameters
        search_term = flow_manager.state.get("pending_search_term", "").strip()
        limit = flow_manager.state.get("pending_search_limit", 3)

        if not search_term or len(search_term) < 2:
            # Import node creator function
            from flows.nodes.service_selection import create_search_retry_node
            return {
                "success": False,
                "message": "Please provide the name of a service to search for.",
                "services": []
            }, create_search_retry_node("Please provide the name of a service to search for.")

        # Use fuzzy search service - this is the actual API call that takes time
        search_result = fuzzy_search_service.search_services(search_term, limit)
        print(search_result)

        if search_result.found and search_result.services:
            # Store services in flow state
            flow_manager.state["services_found"] = search_result.services
            flow_manager.state["current_search_term"] = search_term
            
            services_data = []
            for service in search_result.services:
                services_data.append({
                    "name": service.name,
                    "uuid": service.uuid
                })
            
            result = {
                "success": True,
                "count": search_result.count,
                "services": services_data,
                "search_term": search_term,
                "message": f"Found {search_result.count} services for '{search_term}'"
            }
            
            # Dynamically create service selection node with found services
            from flows.nodes.service_selection import create_service_selection_node
            return result, create_service_selection_node(search_result.services, search_term)
        else:
            # Dynamically create no results node
            error_message = search_result.message or f"No services found for '{search_term}'. Can you please provide the full service name."
            from flows.nodes.service_selection import create_search_retry_node
            return {
                "success": False,
                "message": error_message,
                "services": []
            }, create_search_retry_node(error_message)
    
    except Exception as e:
        logger.error(f"Flow service search error: {e}")
        from flows.nodes.service_selection import create_search_retry_node
        return {
            "success": False,
            "message": "Service search failed. Please try again.",
            "services": []
        }, create_search_retry_node("Service search failed. Please try again.")


async def select_service_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Handle service selection and transition to address collection"""
    service_uuid = args.get("service_uuid", "").strip()
    
    if not service_uuid:
        return {"success": False, "message": "Please select a service"}, None
    
    # Find the selected service from stored services
    services_found = flow_manager.state.get("services_found", [])
    selected_service = None
    
    for service in services_found:
        if service.uuid == service_uuid:
            selected_service = service
            break
    
    if not selected_service:
        return {"success": False, "message": "Service not found"}, None
    
    # Initialize selected services list in state
    if "selected_services" not in flow_manager.state:
        flow_manager.state["selected_services"] = []
    
    # Add selected service (avoid duplicates)
    if selected_service not in flow_manager.state["selected_services"]:
        flow_manager.state["selected_services"].append(selected_service)
    
    logger.info(f"🎯 Service selected: {selected_service.name}")
    
    from flows.nodes.patient_info import create_collect_address_node
    return {
        "success": True, 
        "service_name": selected_service.name,
        "service_uuid": selected_service.uuid
    }, create_collect_address_node()


async def refine_search_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Handle refined search when user wants to speak full service name"""
    refined_term = args.get("refined_search_term", "").strip()
    
    if not refined_term or len(refined_term) < 3:
        return {
            "success": False,
            "message": "Please provide a more specific service name"
        }, None
    
    # Perform new search with refined term
    search_result = fuzzy_search_service.search_services(refined_term, 3)
    
    if search_result.found and search_result.services:
        # Store new search results
        flow_manager.state["services_found"] = search_result.services
        flow_manager.state["current_search_term"] = refined_term
        
        services_data = []
        for service in search_result.services:
            services_data.append({
                "name": service.name,
                "uuid": service.uuid
            })
        
        result = {
            "success": True,
            "count": search_result.count,
            "services": services_data,
            "search_term": refined_term,
            "message": f"Found {search_result.count} services for '{refined_term}'"
        }
        
        from flows.nodes.service_selection import create_service_selection_node
        return result, create_service_selection_node(search_result.services, refined_term)
    else:
        error_message = f"No services found for '{refined_term}'. Try a different term."
        from flows.nodes.service_selection import create_search_retry_node
        return {
            "success": False,
            "message": error_message,
            "services": []
        }, create_search_retry_node(error_message)