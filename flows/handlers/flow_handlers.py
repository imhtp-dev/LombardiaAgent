"""
Flow generation and navigation handlers
"""

import json
from typing import Dict, Any, Tuple
from loguru import logger

from pipecat_flows import FlowManager, NodeConfig, FlowArgs
from services.cerba_api import cerba_api
from services.get_flowNb import genera_flow
from models.requests import HealthService


async def generate_flow_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Generate decision flow for the selected service and transition to flow navigation"""
    try:
        # Get selected services from state
        selected_services = flow_manager.state.get("selected_services", [])
        if not selected_services:
            from flows.nodes.completion import create_error_node
            return {"success": False, "message": "No service selected"}, create_error_node("No service selected. Please restart booking.")
        
        # Get patient info
        gender = flow_manager.state.get("patient_gender")
        date_of_birth = flow_manager.state.get("patient_dob") 
        address = flow_manager.state.get("patient_address")
        
        if not all([gender, date_of_birth, address]):
            from flows.nodes.completion import create_error_node
            return {"success": False, "message": "Missing patient information"}, create_error_node("Missing patient information. Please restart booking.")
        
        # Use first selected service to generate initial flow
        primary_service = selected_services[0]
        
        # Make agent speak during flow generation
        flow_generation_status_text = f"I'm analyzing {primary_service.name} To determine if there are any special requirements or additional options. Please wait..."
        
        # Push TTSSpeakFrame to make agent speak immediately
        from pipecat.frames.frames import TTSSpeakFrame
        if flow_manager.task:
            await flow_manager.task.queue_frames([TTSSpeakFrame(text=flow_generation_status_text)])
        
        # Format date for API call
        dob_formatted = date_of_birth.replace("-", "")
        
        logger.info(f"🔄 Generating decision flow for: {primary_service.name}")
        
        # Get initial health centers to use for flow generation
        health_centers = cerba_api.get_health_centers(
            health_services=[primary_service.uuid],
            gender=gender,
            date_of_birth=dob_formatted,
            address=address
        )
        
        if not health_centers:
            from flows.nodes.booking import create_no_centers_node
            return {
                "success": False,
                "message": f"No health centers found in {address} for {primary_service.name}"
            }, create_no_centers_node(address, primary_service.name)
        
        # Use first available health center for flow generation
        health_center = health_centers[0]
        
        # Generate the decision flow using get_flowNb.py with health centers list
        hc_uuids = [center.uuid for center in health_centers]
        logger.info(f"🔄 Calling genera_flow with: centers={hc_uuids[:3]}, service={primary_service.uuid}")
        generated_flow = genera_flow(
            hc_uuids,  # Pass list of health center UUIDs 
            primary_service.uuid  # Pass medical exam ID
        )
        
        if not generated_flow:
            logger.warning(f"Failed to generate flow for {primary_service.name}, proceeding with direct booking")
            from flows.nodes.booking import create_final_center_search_node
            return {"success": True, "message": "Proceeding to center selection"}, create_final_center_search_node()
        
        # Store the generated flow in state
        flow_manager.state["generated_flow"] = generated_flow
        flow_manager.state["available_centers"] = health_centers[:5]
        
        logger.success(f"✅ Generated decision flow for {primary_service.name}")
        
        result = {
            "success": True,
            "flow_generated": True,
            "service_name": primary_service.name,
            "message": f"Generated decision flow for {primary_service.name}"
        }
        
        # Transition to LLM-driven flow navigation
        from flows.nodes.booking import create_flow_navigation_node
        return result, create_flow_navigation_node(generated_flow, primary_service.name)
        
    except Exception as e:
        logger.error(f"Flow generation error: {e}")
        from flows.nodes.completion import create_error_node
        return {"success": False, "message": "Failed to generate decision flow"}, create_error_node("Failed to generate decision flow. Please try again.")


async def finalize_services_and_search_centers(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Extract final service selections from flow navigation and search centers"""
    try:
        # Get parameters from LLM flow navigation
        additional_services = args.get("additional_services", [])
        specialist_visit_chosen = args.get("specialist_visit_chosen", False)
        flow_path = args.get("flow_path", "")
        
        # Get existing selected services from state
        selected_services = flow_manager.state.get("selected_services", [])
        
        # Get the generated flow to understand what services were offered
        generated_flow = flow_manager.state.get("generated_flow", {})
        
        logger.info(f"🔍 Flow navigation complete:")
        logger.info(f"   Additional services: {additional_services}")
        logger.info(f"   Specialist visit chosen: {specialist_visit_chosen}")
        logger.info(f"   Flow path: {flow_path}")
        logger.info(f"   Original services: {[s.name for s in selected_services]}")
        
        # Add additional services to state (avoid duplicates by UUID)
        existing_uuids = {service.uuid for service in selected_services}
        
        # Process additional services from the decision flow
        for additional_service in additional_services:
            service_uuid = additional_service.get("uuid")
            service_name = additional_service.get("name")
            
            if service_uuid and service_uuid not in existing_uuids:
                # Create HealthService object for consistency
                new_service = HealthService(
                    uuid=service_uuid,
                    name=service_name,
                    code="",  # Will be filled from API if needed
                    synonyms=[]
                )
                selected_services.append(new_service)
                existing_uuids.add(service_uuid)
                logger.success(f"✅ Added additional service: {service_name}")
        
        # Special handling for specialist visit based on flow structure
        if specialist_visit_chosen and generated_flow:
            logger.info(f"👩‍⚕️ User chose specialist visit, analyzing flow structure...")
            
            # Navigate the flow structure based on the path to find specialist services
            try:
                # For this specific flow (option 5), specialist services might be in different places
                # Let's look for services that should be added when specialist visit is chosen
                
                # Check the main flow structure for hidden specialist services
                if "list_health_services" in generated_flow:
                    main_services = generated_flow.get("list_health_services", [])
                    main_uuids = generated_flow.get("list_health_servicesUUID", [])
                    main_codes = generated_flow.get("health_service_code", [])
                    
                    # Look for cardiologist visit in the main services list
                    for i, service_name in enumerate(main_services):
                        # Look for specialist visit services (cardiologist, etc.)
                        if any(keyword in service_name.lower() for keyword in ["visita", "cardiolog", "visit", "specialist"]):
                            if i < len(main_uuids):
                                service_uuid = main_uuids[i]
                                service_code = main_codes[i] if i < len(main_codes) else ""
                                
                                if service_uuid not in existing_uuids:
                                    specialist_service = HealthService(
                                        uuid=service_uuid,
                                        name=service_name,
                                        code=service_code,
                                        synonyms=[]
                                    )
                                    selected_services.append(specialist_service)
                                    existing_uuids.add(service_uuid)
                                    logger.success(f"✅ Added specialist service: {service_name}")
                
            except Exception as e:
                logger.warning(f"Could not parse specialist services from flow: {e}")
        
        # Ensure we have at least the original service
        if not selected_services:
            logger.warning("⚠️  No services in final selection, this shouldn't happen")
            from flows.nodes.completion import create_error_node
            return {"success": False, "message": "No services selected"}, create_error_node("No services selected. Please restart booking.")
        
        flow_manager.state["selected_services"] = selected_services
        
        logger.success(f"🎯 Final service selection: {[s.name for s in selected_services]}")
        logger.success(f"📊 Service count: {len(selected_services)}")
        
        # Transition to final center search with all services
        from flows.nodes.booking import create_final_center_search_node
        return {
            "success": True,
            "final_services": [s.name for s in selected_services],
            "service_count": len(selected_services),
            "specialist_visit": specialist_visit_chosen
        }, create_final_center_search_node()
        
    except Exception as e:
        logger.error(f"Service finalization error: {e}")
        from flows.nodes.completion import create_error_node
        return {"success": False, "message": "Failed to finalize services"}, create_error_node("Failed to finalize services. Please try again.")