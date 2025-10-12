"""
Booking and slot management flow handlers
"""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, Any, Tuple, List
from loguru import logger

from pipecat_flows import FlowManager, NodeConfig, FlowArgs
from services.cerba_api import cerba_api
from services.slotAgenda import list_slot, create_slot, delete_slot
from models.requests import HealthService, HealthCenter


async def search_final_centers_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Search health centers with all selected services and transition to center selection"""
    try:
        # Get all selected services from state
        selected_services = flow_manager.state.get("selected_services", [])
        if not selected_services:
            from flows.nodes.completion import create_error_node
            return {"success": False, "message": "No services selected"}, create_error_node("No services selected. Please restart booking.")
        
        # Get patient information
        gender = flow_manager.state.get("patient_gender")
        date_of_birth = flow_manager.state.get("patient_dob") 
        address = flow_manager.state.get("patient_address")
        
        if not all([gender, date_of_birth, address]):
            from flows.nodes.completion import create_error_node
            return {"success": False, "message": "Missing patient information"}, create_error_node("Missing patient information. Please restart booking.")
        
        # Prepare service UUIDs
        service_uuids = [service.uuid for service in selected_services]
        service_names = [service.name for service in selected_services]
        
        logger.info(f"🏥 Final center search: services={service_names}, gender={gender}, dob={date_of_birth}, address={address}")
        
        # Store center search parameters for processing node
        flow_manager.state["pending_center_search_params"] = {
            "selected_services": selected_services,
            "service_uuids": service_uuids,
            "service_names": service_names,
            "gender": gender,
            "date_of_birth": date_of_birth,
            "address": address
        }

        # Create message based on service count
        if len(service_names) == 1:
            center_search_status_text = f"Sto cercando centri sanitari a {address} che forniscano {service_names[0]}. Attendi..."
        else:
            center_search_status_text = f"Sto cercando centri sanitari a {address} che offrano tutti i servizi selezionati. Attendi..."

        # Create intermediate node with pre_actions for immediate TTS
        from flows.nodes.booking import create_center_search_processing_node
        return {
            "success": True,
            "message": f"Starting center search in {address}"
        }, create_center_search_processing_node(address, center_search_status_text)

    except Exception as e:
        logger.error(f"❌ Center search initialization error: {e}")
        from flows.nodes.completion import create_error_node
        return {
            "success": False,
            "message": "Center search failed. Please try again."
        }, create_error_node("Center search failed. Please try again.")


async def perform_center_search_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Perform the actual center search after TTS message"""
    try:
        # Get stored center search parameters
        params = flow_manager.state.get("pending_center_search_params", {})
        if not params:
            from flows.nodes.completion import create_error_node
            return {
                "success": False,
                "message": "Missing center search parameters"
            }, create_error_node("Missing center search parameters. Please start over.")

        # Extract parameters
        selected_services = params["selected_services"]
        service_uuids = params["service_uuids"]
        service_names = params["service_names"]
        gender = params["gender"]
        date_of_birth = params["date_of_birth"]
        address = params["address"]

        # Format date for API
        dob_formatted = date_of_birth.replace("-", "")
        
        # Call Cerba API with all selected services
        health_centers = cerba_api.get_health_centers(
            health_services=service_uuids,
            gender=gender,
            date_of_birth=dob_formatted,
            address=address
        )
        
        if health_centers:
            flow_manager.state["final_health_centers"] = health_centers[:3]  # Top 3 centers
            
            centers_data = []
            for center in health_centers[:3]:
                centers_data.append({
                    "name": center.name,
                    "city": center.city,
                    "address": center.address,
                    "uuid": center.uuid
                })
            
            result = {
                "success": True,
                "count": len(centers_data),
                "centers": centers_data,
                "services": service_names,
                "message": f"Found {len(centers_data)} health centers in {address} for the selected services"
            }
            
            # Dynamically create final center selection node
            from flows.nodes.booking import create_final_center_selection_node
            return result, create_final_center_selection_node(health_centers[:3], selected_services)
        else:
            # Dynamically create no centers found node
            services_text = ", ".join(service_names)
            error_message = f"No health centers found in {address} for the services: {services_text}"
            from flows.nodes.booking import create_no_centers_node
            return {
                "success": False,
                "message": error_message,
                "centers": []
            }, create_no_centers_node(address, services_text)
    
    except Exception as e:
        logger.error(f"Final center search error: {e}")
        from flows.nodes.completion import create_error_node
        return {"success": False, "message": "Unable to find health centers"}, create_error_node("Unable to find health centers. Please try again.")


async def select_center_and_book(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Handle center selection and proceed to booking confirmation"""
    center_uuid = args.get("center_uuid", "").strip()
    
    if not center_uuid:
        return {"success": False, "message": "Please select a health center"}, None
    
    # Find the selected center from stored centers
    final_centers = flow_manager.state.get("final_health_centers", [])
    selected_center = None
    
    for center in final_centers:
        if center.uuid == center_uuid:
            selected_center = center
            break
    
    if not selected_center:
        return {"success": False, "message": "Health center not found"}, None
    
    # Store selected center
    flow_manager.state["selected_center"] = selected_center
    
    logger.info(f"🏥 Center selected: {selected_center.name} in {selected_center.city}")
    
    from flows.nodes.booking import create_cerba_membership_node
    return {
        "success": True,
        "center_name": selected_center.name,
        "center_city": selected_center.city,
        "center_address": selected_center.address
    }, create_cerba_membership_node()


async def check_cerba_membership_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Check if user is a Cerba member and transition to date/time collection"""
    is_member = args.get("is_cerba_member", False)
    
    # Store membership status for pricing calculations
    flow_manager.state["is_cerba_member"] = is_member
    
    logger.info(f"💳 Cerba membership status: {'Member' if is_member else 'Non-member'}")
    
    from flows.nodes.booking import create_collect_datetime_node
    return {
        "success": True,
        "is_cerba_member": is_member,
        "membership_status": "member" if is_member else "non-member"
    }, create_collect_datetime_node()


async def collect_datetime_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Collect preferred date and optional time preference for appointment"""
    preferred_date = args.get("preferred_date", "").strip()
    preferred_time = args.get("preferred_time", "").strip() 
    time_preference = args.get("time_preference", "any").strip().lower()
    
    if not preferred_date:
        return {"success": False, "message": "Please provide a date for your appointment"}, None
    
    try:
        # Parse and validate date
        date_obj = datetime.strptime(preferred_date, "%Y-%m-%d")
        current_date = datetime.now().date()
        if date_obj.date() < current_date:
            return {"success": False, "message": f"Please select a future date after {current_date.strftime('%Y-%m-%d')}."}, None
        
        # Store date
        flow_manager.state["preferred_date"] = preferred_date
        
        # Handle time preferences - use database time format directly (no timezone conversion)

        if time_preference == "morning" or "morning" in preferred_time.lower():
            # 08:00-12:00 time range (database format)
            flow_manager.state["start_time"] = f"{preferred_date} 08:00:00+00"
            flow_manager.state["end_time"] = f"{preferred_date} 12:00:00+00"
            flow_manager.state["time_preference"] = "morning (08:00-12:00)"
            logger.info(f"📅 Date/Time collected: {preferred_date} - Morning (08:00-12:00)")
        elif time_preference == "afternoon" or "afternoon" in preferred_time.lower():
            # 12:00-19:00 time range (database format)
            flow_manager.state["start_time"] = f"{preferred_date} 12:00:00+00"
            flow_manager.state["end_time"] = f"{preferred_date} 19:00:00+00"
            flow_manager.state["time_preference"] = "afternoon (12:00-19:00)"
            logger.info(f"📅 Date/Time collected: {preferred_date} - Afternoon (12:00-19:00)")
        elif preferred_time and time_preference == "specific":
            # Parse specific time
            time_str = preferred_time.lower().replace("am", "").replace("pm", "").strip()
            if ":" in time_str:
                hour, minute = map(int, time_str.split(":"))
            else:
                hour = int(time_str)
                minute = 0

            # Handle PM times if needed
            if "pm" in preferred_time.lower() and hour != 12:
                hour += 12
            elif "am" in preferred_time.lower() and hour == 12:
                hour = 0

            # Use database time format directly (no timezone conversion)
            end_hour = (hour + 2) % 24  # Add 2 hours for slot window

            flow_manager.state["start_time"] = f"{preferred_date} {hour:02d}:{minute:02d}:00+00"
            flow_manager.state["end_time"] = f"{preferred_date} {end_hour:02d}:{minute:02d}:00+00"
            flow_manager.state["preferred_time"] = f"{hour:02d}:{minute:02d}"
            flow_manager.state["time_preference"] = f"specific time ({hour:02d}:{minute:02d})"
            logger.info(f"📅 Date/Time collected: {preferred_date} at {hour:02d}:{minute:02d}")
        else:
            # No specific time preference - use full day range
            flow_manager.state["start_time"] = None
            flow_manager.state["end_time"] = None
            flow_manager.state["time_preference"] = "any time"
            logger.info(f"📅 Date collected: {preferred_date} - No time preference")
        
        from flows.nodes.booking import create_slot_search_node
        return {
            "success": True,
            "preferred_date": preferred_date,
            "time_preference": flow_manager.state.get("time_preference", "any time")
        }, create_slot_search_node()
        
    except (ValueError, TypeError) as e:
        logger.error(f"Date/time parsing error: {e}")
        return {"success": False, "message": "Invalid date format. Please use a valid date like 'November 21' or '2025-11-21'"}, None


async def update_date_and_search_slots(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Update date preference and immediately search for slots - optimized for date selection flow"""
    preferred_date = args.get("preferred_date", "").strip()
    time_preference = args.get("time_preference", "preserve_existing").strip()

    if not preferred_date:
        return {"success": False, "message": "Please provide a date for your appointment"}, None

    try:
        # Parse and validate date
        date_obj = datetime.strptime(preferred_date, "%Y-%m-%d")
        current_date = datetime.now().date()
        if date_obj.date() < current_date:
            return {"success": False, "message": f"Please select a future date after {current_date.strftime('%Y-%m-%d')}."}, None

        # Store new date
        flow_manager.state["preferred_date"] = preferred_date
        logger.info(f"📅 Updated preferred date to: {preferred_date}")

        # Handle time preference
        if time_preference == "preserve_existing":
            # Keep existing time preference if available
            existing_time_pref = flow_manager.state.get("time_preference", "any time")
            logger.info(f"🕐 Preserving existing time preference: {existing_time_pref}")
        else:
            # Update time preference and time ranges
            if time_preference == "morning":
                flow_manager.state["start_time"] = f"{preferred_date} 08:00:00+00"
                flow_manager.state["end_time"] = f"{preferred_date} 12:00:00+00"
                flow_manager.state["time_preference"] = "morning (08:00-12:00)"
            elif time_preference == "afternoon":
                flow_manager.state["start_time"] = f"{preferred_date} 12:00:00+00"
                flow_manager.state["end_time"] = f"{preferred_date} 19:00:00+00"
                flow_manager.state["time_preference"] = "afternoon (12:00-19:00)"
            else:
                # 'any' preference - no time constraints
                flow_manager.state["start_time"] = None
                flow_manager.state["end_time"] = None
                flow_manager.state["time_preference"] = "any time"

            logger.info(f"🕐 Updated time preference to: {flow_manager.state.get('time_preference')}")

        # Immediately perform slot search with updated parameters
        selected_center = flow_manager.state.get("selected_center")
        selected_services = flow_manager.state.get("selected_services", [])
        start_time = flow_manager.state.get("start_time")
        end_time = flow_manager.state.get("end_time")
        patient_gender = flow_manager.state.get("patient_gender", 'm')
        patient_dob = flow_manager.state.get("patient_dob", "1980-04-13")

        if not selected_center or not selected_services:
            from flows.nodes.completion import create_error_node
            return {"success": False, "message": "Missing booking details"}, create_error_node("Missing booking details. Please start over.")

        current_service_index = flow_manager.state.get("current_service_index", 0)
        current_service = selected_services[current_service_index]

        # Format DOB for API
        dob_formatted = patient_dob.replace("-", "")

        logger.info(f"🔍 Searching slots for {current_service.name} on {preferred_date}")

        # Call list_slot directly
        from services.slotAgenda import list_slot
        slots_response = list_slot(
            health_center_uuid=selected_center.uuid,
            date_search=preferred_date,
            uuid_exam=[current_service.uuid],
            gender=patient_gender,
            date_of_birth=dob_formatted,
            start_time=start_time,
            end_time=end_time
        )

        if slots_response and len(slots_response) > 0:
            # Store available slots
            flow_manager.state["available_slots"] = slots_response
            flow_manager.state["current_service_index"] = current_service_index

            logger.success(f"✅ Found {len(slots_response)} available slots for {preferred_date}")

            # Create new slot selection node with the found slots
            from flows.nodes.booking import create_slot_selection_node

            user_preferred_date = flow_manager.state.get("preferred_date")
            time_preference_state = flow_manager.state.get("time_preference", "any time")

            return {
                "success": True,
                "slots_count": len(slots_response),
                "service_name": current_service.name,
                "message": f"Found {len(slots_response)} available slots for {preferred_date}"
            }, create_slot_selection_node(
                slots=slots_response,
                service=current_service,
                is_cerba_member=flow_manager.state.get("is_cerba_member", False),
                user_preferred_date=user_preferred_date,
                time_preference=time_preference_state
            )
        else:
            error_message = f"No available slots found for {current_service.name} on {preferred_date}"
            logger.warning(f"⚠️ {error_message}")

            # Go to no slots node with suggestion for different dates
            from flows.nodes.booking import create_no_slots_node
            return {
                "success": False,
                "message": error_message
            }, create_no_slots_node(preferred_date, flow_manager.state.get("time_preference", "any time"))

    except (ValueError, TypeError) as e:
        logger.error(f"Date parsing error: {e}")
        return {"success": False, "message": "Invalid date format. Please use format YYYY-MM-DD (e.g., '2025-11-26')"}, None


async def search_slots_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Search for available slots and transition to slot selection or direct booking"""
    try:
        # Get booking details from state
        selected_center = flow_manager.state.get("selected_center")
        selected_services = flow_manager.state.get("selected_services", [])
        preferred_date = flow_manager.state.get("preferred_date")
        start_time = flow_manager.state.get("start_time")  # Optional
        end_time = flow_manager.state.get("end_time")      # Optional
        time_preference = flow_manager.state.get("time_preference", "any time")
        patient_gender = flow_manager.state.get("patient_gender", 'm')
        patient_dob = flow_manager.state.get("patient_dob", '1980-04-13')
        current_service_index = flow_manager.state.get("current_service_index", 0)
        
        if not all([selected_center, selected_services, preferred_date]):
            from flows.nodes.completion import create_error_node
            return {"success": False, "message": "Missing booking information"}, create_error_node("Missing booking information. Please restart.")
        
        # Get current service being processed
        current_service = selected_services[current_service_index]

        # Store slot search parameters for processing node
        flow_manager.state["pending_slot_search_params"] = {
            "selected_center": selected_center,
            "selected_services": selected_services,
            "preferred_date": preferred_date,
            "start_time": start_time,
            "end_time": end_time,
            "time_preference": time_preference,
            "patient_gender": patient_gender,
            "patient_dob": patient_dob,
            "current_service_index": current_service_index,
            "current_service": current_service
        }

        # Create status message based on service count
        if len(selected_services) > 1:
            status_text = f"Ricerca di slot disponibili per {current_service.name}, servizio {current_service_index + 1} di {len(selected_services)}. Attendi..."
        else:
            status_text = f"Ricerca di slot disponibili per {current_service.name}. Attendi..."

        # Create intermediate node with pre_actions for immediate TTS
        from flows.nodes.booking import create_slot_search_processing_node
        return {
            "success": True,
            "message": f"Starting slot search for {current_service.name}"
        }, create_slot_search_processing_node(current_service.name, status_text)

    except Exception as e:
        logger.error(f"❌ Slot search initialization error: {e}")
        from flows.nodes.completion import create_error_node
        return {
            "success": False,
            "message": "Slot search failed. Please try again."
        }, create_error_node("Slot search failed. Please try again.")


async def perform_slot_search_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Perform the actual slot search after TTS message"""
    try:
        # Get stored slot search parameters
        params = flow_manager.state.get("pending_slot_search_params", {})
        if not params:
            from flows.nodes.completion import create_error_node
            return {
                "success": False,
                "message": "Missing slot search parameters"
            }, create_error_node("Missing slot search parameters. Please start over.")

        # Extract parameters
        selected_center = params["selected_center"]
        selected_services = params["selected_services"]
        preferred_date = params["preferred_date"]
        start_time = params["start_time"]
        end_time = params["end_time"]
        time_preference = params["time_preference"]
        patient_gender = params["patient_gender"]
        patient_dob = params["patient_dob"]
        current_service_index = params["current_service_index"]
        current_service = params["current_service"]

        # Format date of birth for API (remove dashes)
        dob_formatted = patient_dob.replace("-", "")
        
        logger.info(f"🔍 Searching slots for {current_service.name} at {selected_center.name}")
        logger.info(f"🕐 Time preference: {time_preference}")
        logger.info(f"👤 Patient: Gender={patient_gender}, DOB={dob_formatted}")
        
        # Call list_slot with optional start/end times
        slots_response = list_slot(
            health_center_uuid=selected_center.uuid,
            date_search=preferred_date,
            uuid_exam=[current_service.uuid],  # Only current service
            gender=patient_gender,
            date_of_birth=dob_formatted,
            start_time=start_time,  # Will be None if no time preference
            end_time=end_time       # Will be None if no time preference
        )
        
        if slots_response and len(slots_response) > 0:
            # Store available slots
            flow_manager.state["available_slots"] = slots_response
            flow_manager.state["current_service_index"] = current_service_index
            
            logger.success(f"✅ Found {len(slots_response)} available slots")
            
            from flows.nodes.booking import create_slot_selection_node

            # Pass user preferences for smart filtering
            user_preferred_date = flow_manager.state.get("preferred_date")

            logger.info(f"🚀 SMART FILTERING: Calling slot selection with:")
            logger.info(f"   - user_preferred_date: {user_preferred_date}")
            logger.info(f"   - time_preference: {time_preference}")
            logger.info(f"   - total_slots: {len(slots_response)}")

            return {
                "success": True,
                "slots_count": len(slots_response),
                "service_name": current_service.name,
                "time_preference": time_preference,
                "message": "Slot search completed"
            }, create_slot_selection_node(
                slots=slots_response,
                service=current_service,
                is_cerba_member=flow_manager.state.get("is_cerba_member", False),
                user_preferred_date=user_preferred_date,
                time_preference=time_preference
            )
        else:
            error_message = f"No available slots found for {current_service.name} on {preferred_date}"
            if time_preference != "any time":
                error_message += f" for {time_preference}"
            
            from flows.nodes.booking import create_no_slots_node
            return {
                "success": False,
                "message": error_message
            }, create_no_slots_node(preferred_date, time_preference)
            
    except Exception as e:
        logger.error(f"Slot search error: {e}")
        from flows.nodes.completion import create_error_node
        return {"success": False, "message": "Failed to search for available slots"}, create_error_node("Failed to search slots. Please try again.")


async def select_slot_and_book(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Handle slot selection and proceed to booking creation"""
    providing_entity_availability_uuid = args.get("providing_entity_availability_uuid", "").strip()
    selected_time = args.get("selected_time", "").strip()
    selected_date = args.get("selected_date", "").strip()

    # COMPREHENSIVE DEBUG LOGGING FOR SLOT SELECTION
    logger.info("🔍 DEBUG: === SLOT SELECTION STARTED ===")
    logger.info(f"🔍 DEBUG: Args received: {args}")
    logger.info(f"🔍 DEBUG: providing_entity_availability_uuid = '{providing_entity_availability_uuid}'")
    logger.info(f"🔍 DEBUG: selected_time = '{selected_time}'")
    logger.info(f"🔍 DEBUG: selected_date = '{selected_date}'")

    if not providing_entity_availability_uuid:
        logger.error("❌ DEBUG: No providing_entity_availability_uuid provided!")
        return {"success": False, "message": "Please select a time slot"}, None

    # Find selected slot from available slots using both UUID and time for precise matching
    available_slots = flow_manager.state.get("available_slots", [])
    selected_slot = None

    logger.info(f"🔍 DEBUG: available_slots count = {len(available_slots) if available_slots else 0}")
    logger.info(f"🔍 DEBUG: available_slots = {available_slots}")

    logger.info(f"🔍 Searching for slot: UUID={providing_entity_availability_uuid}, Time={selected_time}, Date={selected_date}")

    # SMART LOOKUP: Check if we have time→UUID mapping from smart filtering
    from flows.nodes.booking import _current_session_slots
    if selected_time and selected_time in _current_session_slots:
        logger.info(f"🎯 SMART LOOKUP: Found slot by time '{selected_time}' in filtered session slots")
        selected_slot = _current_session_slots[selected_time]['original']
        logger.info(f"✅ Using smart-filtered slot: UUID={selected_slot.get('providing_entity_availability_uuid')}")
    else:
        logger.info(f"🔍 FALLBACK: Using traditional UUID/time matching in all {len(available_slots)} slots")

        for slot in available_slots:
            if slot.get("providing_entity_availability_uuid") == providing_entity_availability_uuid:
                # If we have time info, use it for precise matching
                if selected_time:
                    # IMPORTANT: Convert UTC database times to Italian local time for comparison
                    # because user selected Italian time but database has UTC times
                    from services.timezone_utils import utc_to_italian_display

                    italian_start = utc_to_italian_display(slot.get("start_time", ""))
                    italian_end = utc_to_italian_display(slot.get("end_time", ""))

                    try:
                        if not italian_start or not italian_end:
                            # Fallback to original method if conversion fails
                            logger.warning(f"⚠️ Timezone conversion failed for slot comparison, using UTC times")
                            start_time_str = slot.get("start_time", "").replace("T", " ").replace("+00:00", "")
                            end_time_str = slot.get("end_time", "").replace("T", " ").replace("+00:00", "")
                            start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                            end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
                        else:
                            # Use converted Italian times for comparison
                            start_dt = datetime.strptime(italian_start, "%Y-%m-%d %H:%M:%S")
                            end_dt = datetime.strptime(italian_end, "%Y-%m-%d %H:%M:%S")

                        # Format slot time to match selected_time format (H:MM - H:MM)
                        slot_time_full = f"{start_dt.strftime('%-H:%M')} - {end_dt.strftime('%-H:%M')}"
                        slot_time_start = start_dt.strftime('%-H:%M')

                        # Normalize times for comparison (remove leading zeros from both)
                        normalized_selected = selected_time.lstrip('0').replace(':0', ':') if selected_time.startswith('0') else selected_time
                        normalized_slot_start = slot_time_start

                        # Also try parsing selected_time to check if it falls within the slot range
                        selected_dt = None
                        try:
                            # Parse the selected time on the same date
                            selected_time_clean = selected_time.replace(':', ':').strip()
                            if ':' in selected_time_clean:
                                hour_min = selected_time_clean.split(':')
                                hour = int(hour_min[0])
                                minute = int(hour_min[1]) if len(hour_min) > 1 else 0
                                selected_dt = start_dt.replace(hour=hour, minute=minute)
                        except Exception:
                            pass

                        logger.info(f"🕐 Comparing times: slot='{slot_time_full}' (Italian) vs selected='{selected_time}' (normalized: '{normalized_selected}') vs slot_start='{normalized_slot_start}'")

                        # Match multiple ways:
                        # 1. Exact slot start time match (normalized)
                        # 2. Selected time falls within slot time range
                        # 3. Full format match
                        time_matches = (
                            normalized_slot_start == normalized_selected or  # Start time match
                            normalized_slot_start == selected_time or        # Direct match
                            slot_time_start == selected_time or              # Exact match
                            slot_time_full == selected_time or               # Full range match
                            (selected_dt and start_dt <= selected_dt < end_dt)  # Falls within range
                        )

                        if time_matches:
                            selected_slot = slot
                            logger.info(f"✅ Found exact time match: {slot_time_full}")
                            break
                    except Exception as e:
                        logger.warning(f"⚠️ Time parsing error for slot: {e}")
                        # Continue to check other slots
                        continue
                else:
                    # Fallback to first match by UUID (old behavior)
                    selected_slot = slot
                    logger.warning(f"⚠️ Using UUID-only matching (no time provided)")
                    break

    if not selected_slot:
        logger.error(f"❌ DEBUG: Slot not found: UUID={providing_entity_availability_uuid}, Time={selected_time}")

        # Debug: Log all available UUIDs for comparison
        logger.error("❌ DEBUG: Available slot UUIDs:")
        for i, slot in enumerate(available_slots):
            uuid = slot.get("providing_entity_availability_uuid", "MISSING_UUID")
            logger.error(f"   [{i}] UUID: {uuid}")

        # Provide more helpful error message with available times (in Italian local time)
        if available_slots:
            available_times = []
            from services.timezone_utils import utc_to_italian_display

            for slot in available_slots[:5]:  # Show first 5 available times
                try:
                    # Convert UTC to Italian time for user display
                    italian_start = utc_to_italian_display(slot.get("start_time", ""))
                    if italian_start:
                        start_dt = datetime.strptime(italian_start, "%Y-%m-%d %H:%M:%S")
                        available_times.append(start_dt.strftime('%-H:%M'))
                    else:
                        # Fallback to UTC if conversion fails
                        start_time_str = slot.get("start_time", "").replace("T", " ").replace("+00:00", "")
                        start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                        available_times.append(start_dt.strftime('%-H:%M'))
                except:
                    continue

            if available_times:
                times_text = ", ".join(available_times)
                error_message = f"Sorry, that time is not available. Available times include: {times_text}. Please choose one of these times."
            else:
                error_message = "Sorry, that time slot is not available. Please choose from the available times shown above."
        else:
            error_message = "No available slots found. Please try a different date."

        return {"success": False, "message": error_message}, None

    # Store selected slot
    logger.info(f"🔍 DEBUG: STORING selected_slot in state: {selected_slot}")
    flow_manager.state["selected_slot"] = selected_slot
    logger.info(f"🔍 DEBUG: State after storing selected_slot: selected_slot key exists = {'selected_slot' in flow_manager.state}")

    # Extract pricing based on Cerba membership
    is_cerba_member = flow_manager.state.get("is_cerba_member", False)
    health_services = selected_slot.get("health_services", [])

    logger.info(f"🔍 DEBUG: is_cerba_member = {is_cerba_member}")
    logger.info(f"🔍 DEBUG: health_services = {health_services}")

    if health_services:
        service = health_services[0]
        price = service.get("cerba_card_price") if is_cerba_member else service.get("price")
        flow_manager.state["slot_price"] = price
        logger.info(f"🔍 DEBUG: Stored slot_price = {price}")

    logger.info(f"🎯 Slot selected: {selected_slot['start_time']} to {selected_slot['end_time']}")
    logger.info(f"🔍 DEBUG: === SLOT SELECTION COMPLETED SUCCESSFULLY ===")

    # NOTE: Slot reservation will happen in the next step (perform_slot_booking_and_transition)
    # This avoids double reservation attempts

    # Get required data for booking summary
    selected_services = flow_manager.state.get("selected_services", [])
    selected_center = flow_manager.state.get("selected_center")

    if not selected_services or not selected_center:
        return {"success": False, "message": "Missing booking information"}, None

    # Calculate total cost
    total_cost = 0
    selected_slots = [selected_slot]  # For now, single slot

    for service_data in health_services:
        price = service_data.get("cerba_card_price") if is_cerba_member else service_data.get("price", 0)
        total_cost += price

    # Store slot price for later use
    individual_slot_price = 0
    if health_services:
        service_data = health_services[0]
        individual_slot_price = service_data.get("cerba_card_price") if is_cerba_member else service_data.get("price", 0)

    flow_manager.state["slot_price"] = individual_slot_price

    # Go to slot booking creation first (this will reserve the slot)
    from flows.nodes.booking import create_slot_booking_processing_node

    # Debug logging to track slot booking data
    logger.info(f"🎯 Going to slot booking creation:")
    logger.info(f"   Selected slot time: {selected_slot['start_time']} to {selected_slot['end_time']}")
    logger.info(f"   Individual price: {individual_slot_price} euro")
    logger.info(f"   Total cost: {total_cost} euro")
    logger.info(f"   Center: {selected_center.name}")

    # Store slot booking parameters for the processing node
    flow_manager.state["pending_slot_booking_params"] = {
        "selected_slot": selected_slot,
        "selected_services": selected_services,
        "current_service_index": 0  # Single service booking
    }

    # Create status message for slot booking
    current_service_name = selected_services[0].name if selected_services else "your appointment"
    slot_creation_status_text = f"Prenotazione della fascia oraria per {current_service_name}. Attendi..."

    return {
        "success": True,
        "slot_time": f"{selected_slot['start_time']} to {selected_slot['end_time']}",
        "providing_entity_availability_uuid": providing_entity_availability_uuid,
        "message": f"Starting slot reservation for {current_service_name}"
    }, create_slot_booking_processing_node(current_service_name, slot_creation_status_text)


async def create_booking_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Create the slot reservation using create_slot function"""
    confirm_booking = args.get("confirm_booking", False)
    
    if not confirm_booking:
        from flows.nodes.completion import create_restart_node
        return {"success": False, "message": "Booking cancelled"}, create_restart_node()
    
    try:
        selected_slot = flow_manager.state.get("selected_slot")
        selected_services = flow_manager.state.get("selected_services", [])
        current_service_index = flow_manager.state.get("current_service_index", 0)
        
        if not selected_slot:
            from flows.nodes.completion import create_error_node
            return {"success": False, "message": "No slot selected"}, create_error_node("No slot selected.")
        
        # Store slot booking parameters for processing node
        flow_manager.state["pending_slot_booking_params"] = {
            "selected_slot": selected_slot,
            "selected_services": selected_services,
            "current_service_index": current_service_index
        }

        # Create status message
        current_service_name = selected_services[current_service_index].name if current_service_index < len(selected_services) else "your appointment"
        slot_creation_status_text = f"Prenotazione della fascia oraria per {current_service_name}. Attendi..."

        # Create intermediate node with pre_actions for immediate TTS
        from flows.nodes.booking import create_slot_booking_processing_node
        return {
            "success": True,
            "message": f"Starting slot booking for {current_service_name}"
        }, create_slot_booking_processing_node(current_service_name, slot_creation_status_text)

    except Exception as e:
        logger.error(f"❌ Slot booking initialization error: {e}")
        from flows.nodes.completion import create_error_node
        return {
            "success": False,
            "message": "Slot booking failed. Please try again."
        }, create_error_node("Slot booking failed. Please try again.")


async def perform_slot_booking_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Perform the actual slot booking after TTS message"""
    try:
        # Get stored slot booking parameters
        params = flow_manager.state.get("pending_slot_booking_params", {})
        if not params:
            from flows.nodes.completion import create_error_node
            return {
                "success": False,
                "message": "Missing slot booking parameters"
            }, create_error_node("Missing slot booking parameters. Please start over.")

        # Extract parameters
        selected_slot = params["selected_slot"]
        selected_services = params["selected_services"]
        current_service_index = params["current_service_index"]

        # Extract booking details
        start_time = selected_slot["start_time"]
        end_time = selected_slot["end_time"]
        providing_entity_availability = selected_slot["providing_entity_availability_uuid"]
        
        # Convert datetime format for create_slot function
        start_slot = start_time.replace("T", " ").replace("+00:00", "")
        end_slot = end_time.replace("T", " ").replace("+00:00", "")
        
        logger.info(f"📝 Creating slot reservation: {start_slot} to {end_slot}")

        # Call create_slot function (this reserves the slot)
        status_code, slot_uuid, created_at = create_slot(start_slot, end_slot, providing_entity_availability)

        if status_code == 200 or status_code == 201:
            
            # Store slot reservation information
            if "booked_slots" not in flow_manager.state:
                flow_manager.state["booked_slots"] = []
            
            flow_manager.state["booked_slots"].append({
                "slot_uuid": slot_uuid,
                "service_name": selected_services[current_service_index].name,
                "start_time": start_time,
                "end_time": end_time,
                "price": flow_manager.state.get("slot_price", 0)
            })
            
            logger.success(f"✅ Slot reserved successfully: {slot_uuid}")
            
            # Check if there are more services to book
            if current_service_index + 1 < len(selected_services):
                # More services to book - continue with slot creation for next service
                flow_manager.state["current_service_index"] = current_service_index + 1
                next_service = selected_services[current_service_index + 1]

                from flows.nodes.booking import create_collect_datetime_node_for_service
                return {
                    "success": True,
                    "booking_id": slot_uuid,
                    "service_name": selected_services[current_service_index].name,
                    "has_more_services": True,
                    "next_service": next_service.name,
                    "remaining_services": len(selected_services) - current_service_index - 1
                }, create_collect_datetime_node_for_service(next_service.name, True)  # Ask for time for next service
            else:
                # All services have slots reserved - show booking summary
                logger.info(f"🎯 Slot reserved successfully, showing booking summary")

                # Get required data for booking summary
                selected_services = flow_manager.state.get("selected_services", [])
                selected_center = flow_manager.state.get("selected_center")
                is_cerba_member = flow_manager.state.get("is_cerba_member", False)

                # Calculate total cost
                total_cost = 0
                selected_slots = flow_manager.state.get("booked_slots", [])

                for slot_data in selected_slots:
                    total_cost += slot_data.get("price", 0)

                from flows.nodes.booking import create_booking_summary_confirmation_node
                return {
                    "success": True,
                    "slot_id": slot_uuid,
                    "all_slots_created": True,
                    "total_slots": len(flow_manager.state["booked_slots"]),
                    "message": "Perfect! Your time slot has been reserved."
                }, create_booking_summary_confirmation_node(selected_services, selected_slots, selected_center, total_cost, is_cerba_member)
        else:
            # Handle specific error cases
            error_msg = f"Slot reservation failed: HTTP {status_code}"
            logger.error(error_msg)

            # For status code errors, assume slot is no longer available
            if status_code == 409:
                # Slot no longer available - refresh slots
                current_service_name = selected_services[current_service_index].name
                from flows.nodes.booking import create_slot_refresh_node
                return {
                    "success": False,
                    "message": f"Sorry, that time slot is no longer available for {current_service_name}. Let me show you updated available times.",
                    "error_type": "slot_unavailable"
                }, create_slot_refresh_node(current_service_name)
            else:
                # Other booking error
                from flows.nodes.completion import create_error_node
                return {
                    "success": False,
                    "message": "There was an issue creating your booking. Please try again.",
                    "error_type": "booking_failed"
                }, create_error_node("Booking failed. Please try again.")
            
    except Exception as e:
        logger.error(f"Booking creation error: {e}")
        from flows.nodes.completion import create_error_node
        return {"success": False, "message": "Failed to create booking"}, create_error_node("Booking creation failed. Please try again.")


async def handle_booking_modification(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Handle booking cancellation/modification"""
    action = args.get("action", "").lower()
    
    if action == "cancel":
        booked_slots = flow_manager.state.get("booked_slots", [])
        
        if not booked_slots:
            return {"success": False, "message": "No bookings to cancel"}, None
        
        try:
            # Cancel all booked slots
            cancelled_slots = []
            for slot in booked_slots:
                slot_uuid = slot["slot_uuid"]
                delete_response = delete_slot(slot_uuid)
                
                if delete_response.status_code == 200:
                    cancelled_slots.append(slot)
                    logger.info(f"🗑️ Cancelled booking: {slot_uuid}")
            
            # Clear booked slots from state
            flow_manager.state["booked_slots"] = []
            
            from flows.nodes.completion import create_restart_node
            return {
                "success": True,
                "cancelled_count": len(cancelled_slots),
                "message": f"Successfully cancelled {len(cancelled_slots)} booking(s)"
            }, create_restart_node()
            
        except Exception as e:
            logger.error(f"Cancellation error: {e}")
            return {"success": False, "message": "Failed to cancel bookings"}, None
    
    elif action == "change_time":
        # Cancel existing bookings first, then redirect to date/time collection
        booked_slots = flow_manager.state.get("booked_slots", [])
        if booked_slots:
            for slot in booked_slots:
                try:
                    delete_slot(slot["slot_uuid"])
                    logger.info(f"🗑️ Cancelled booking for rescheduling: {slot['slot_uuid']}")
                except:
                    pass
            flow_manager.state["booked_slots"] = []
        
        from flows.nodes.booking import create_collect_datetime_node
        return {
            "success": True,
            "message": "Let's reschedule your appointment"
        }, create_collect_datetime_node()
    
    else:
        return {"success": False, "message": "Please specify 'cancel' or 'change_time'"}, None


async def confirm_booking_summary_and_proceed(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Handle booking summary confirmation and proceed accordingly"""
    action = args.get("action", "")

    if action == "proceed":
        logger.info("✅ Booking summary confirmed, proceeding to collect personal information")

        # Transition to name collection to start personal info gathering
        from flows.nodes.patient_details import create_collect_name_node
        return {
            "success": True,
            "message": "Booking confirmed, starting personal information collection"
        }, create_collect_name_node()

    elif action == "cancel":
        logger.info("❌ Patient cancelled booking due to cost/preferences")

        # Go to restart/cancellation flow
        from flows.nodes.completion import create_restart_node
        return {
            "success": False,
            "message": "Booking cancelled as requested"
        }, create_restart_node()

    elif action == "change":
        logger.info("🔄 Patient wants to change booking details")

        # Instead of restarting completely, go back to slot selection with available slots
        # This preserves the service, center, and date but allows time change
        available_slots = flow_manager.state.get("available_slots", [])
        selected_services = flow_manager.state.get("selected_services", [])
        current_service_index = flow_manager.state.get("current_service_index", 0)

        if available_slots and selected_services:
            current_service = selected_services[current_service_index]
            user_preferred_date = flow_manager.state.get("preferred_date")
            time_preference = flow_manager.state.get("time_preference", "any time")

            logger.info(f"🔄 Returning to slot selection for {current_service.name}")

            from flows.nodes.booking import create_slot_selection_node
            return {
                "success": True,
                "message": "Let's find you a different time slot"
            }, create_slot_selection_node(
                slots=available_slots,
                service=current_service,
                is_cerba_member=flow_manager.state.get("is_cerba_member", False),
                user_preferred_date=user_preferred_date,
                time_preference=time_preference
            )
        else:
            # Fallback: go back to date/time selection
            logger.warning("⚠️ No available slots stored, going back to date selection")
            from flows.nodes.booking import create_collect_datetime_node
            return {
                "success": False,
                "message": "Let's choose a different date and time"
            }, create_collect_datetime_node()

    else:
        return {"success": False, "message": "Please let me know if you want to proceed, cancel, or change the booking"}, None