"""
Patient detail collection flow handlers
"""

from typing import Dict, Any, Tuple
from loguru import logger

from pipecat_flows import FlowManager, NodeConfig, FlowArgs
from services.fiscal_code_generator import fiscal_code_generator
from services.call_logger import call_logger


async def start_email_collection_with_stt_switch(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Handler for starting email collection with STT switch - used when testing email node directly"""
    # STT SWITCHING DISABLED FOR TESTING - keep using Nova-2
    # from utils.stt_switcher import switch_to_email_transcription
    # await switch_to_email_transcription()

    # Transition to email collection
    from flows.nodes.patient_details import create_collect_email_node
    return {
        "success": True,
        "message": "Starting email collection with Nova-2 transcription"
    }, create_collect_email_node()


async def collect_name_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Collect patient name and transition to surname collection"""
    name = args.get("name", "").strip()

    if not name or len(name) < 1:
        return {"success": False, "message": "Please provide your name"}, None

    # Store name in state
    flow_manager.state["patient_name"] = name

    logger.info(f"👤 Patient name collected: {name}")

    from flows.nodes.patient_details import create_collect_surname_node
    return {
        "success": True,
        "name": name,
        "message": "Name collected successfully"
    }, create_collect_surname_node()


async def collect_surname_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Collect patient surname and transition to phone collection"""
    surname = args.get("surname", "").strip()

    if not surname or len(surname) < 1:
        return {"success": False, "message": "Please provide your surname"}, None

    # Store surname in state
    flow_manager.state["patient_surname"] = surname

    logger.info(f"👤 Patient surname collected: {surname}")

    from flows.nodes.patient_details import create_collect_phone_node
    return {
        "success": True,
        "surname": surname,
        "message": "Surname collected successfully"
    }, create_collect_phone_node()


async def collect_phone_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Collect patient phone and transition to phone confirmation"""
    phone = args.get("phone", "").strip().lower()
    raw_phone = args.get("phone", "")  # Keep original for debugging

    # Check if user confirmed to use the calling number
    caller_phone_from_talkdesk = flow_manager.state.get("caller_phone_from_talkdesk", "")

    # DEBUG: Log what we received
    call_logger.log_phone_debug("PHONE_CONFIRMATION_ATTEMPT", {
        "user_said": phone,
        "raw_user_input": raw_phone,  # Add raw input for debugging
        "caller_phone_from_talkdesk": caller_phone_from_talkdesk,
        "flow_state_keys": list(flow_manager.state.keys()),
        "all_flow_state": {k: str(v)[:100] for k, v in flow_manager.state.items()}  # Truncate long values
    })

    # CRITICAL DEBUG: If phone is empty, log this as a major issue
    if not phone.strip():
        call_logger.log_error(Exception("LLM called collect_phone with EMPTY phone parameter!"), {
            "raw_args": str(args),
            "expected": "User response should be passed in phone parameter",
            "debug_tip": "Check LLM function calling behavior"
        })

    # If user says "yes" and we have caller phone from Talkdesk, use it
    if phone in ["yes", "si", "sì", "correct", "okay", "ok", "va bene"] and caller_phone_from_talkdesk:
        phone_clean = ''.join(filter(str.isdigit, caller_phone_from_talkdesk))
        logger.info(f"📞 Using caller's phone number from Talkdesk: {phone_clean}")
    else:
        # DEBUG: Why didn't we use the Talkdesk phone?
        if phone in ["yes", "si", "sì", "correct", "okay", "ok", "va bene"]:
            call_logger.log_error(Exception("User confirmed but NO caller_phone_from_talkdesk found!"), {
                "user_input": phone,
                "expected_phone": "caller_phone_from_talkdesk should exist",
                "flow_state": {k: str(v)[:50] for k, v in flow_manager.state.items()}
            })
        else:
            call_logger.log_phone_debug("USER_DID_NOT_CONFIRM", {
                "user_input": phone,
                "reason": "User provided different phone number"
            })
        # User provided a different phone number
        if not phone or len(phone) < 8:
            return {"success": False, "message": "Please provide a valid phone number"}, None

        # Clean phone number (remove spaces, dashes, etc.)
        phone_clean = ''.join(filter(str.isdigit, phone))

        if len(phone_clean) < 8:
            return {"success": False, "message": "Please provide a valid phone number with at least 8 digits"}, None

        logger.info(f"📞 Patient provided different phone: {phone_clean}")

    # Store phone in state
    flow_manager.state["patient_phone"] = phone_clean

    logger.info(f"📞 Patient phone collected: {phone_clean}")

    # Go to phone confirmation
    from flows.nodes.patient_details import create_confirm_phone_node
    return {
        "success": True,
        "phone": phone_clean,
        "message": "Phone number collected successfully"
    }, create_confirm_phone_node(phone_clean)


async def confirm_phone_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Confirm phone number and transition to email collection"""
    action = args.get("action", "")

    if action == "confirm":
        logger.info("✅ Phone confirmed, proceeding to email collection")

        # STT SWITCHING DISABLED FOR TESTING - keep using Nova-2
        # from utils.stt_switcher import switch_to_email_transcription
        # await switch_to_email_transcription()

        from flows.nodes.patient_details import create_collect_email_node
        return {
            "success": True,
            "message": "Phone confirmed, proceeding to email collection"
        }, create_collect_email_node()

    elif action == "change":
        logger.info("🔄 Phone needs to be changed, returning to phone collection")

        from flows.nodes.patient_details import create_collect_phone_node
        return {
            "success": False,
            "message": "Let's collect your phone number again"
        }, create_collect_phone_node()

    else:
        return {"success": False, "message": "Please confirm if the phone number is correct or if you want to change it"}, None


async def collect_email_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Collect patient email with enhanced validation and transition to fiscal code collection"""
    email = args.get("email", "").strip().lower()

    if not email or "@" not in email or "." not in email:
        return {"success": False, "message": "Please provide a valid email address. Make sure to include @ and a domain."}, None

    # Enhanced email validation
    email_parts = email.split("@")
    if len(email_parts) != 2 or len(email_parts[0]) < 1 or len(email_parts[1]) < 3:
        return {"success": False, "message": "Invalid email format. Please try again with a complete email."}, None

    # Additional validation for common email patterns
    domain_part = email_parts[1]
    if "." not in domain_part or domain_part.startswith(".") or domain_part.endswith("."):
        return {"success": False, "message": "The email domain is not valid. Please try again."}, None

    # Clean up common speech-to-text errors
    email = email.replace(" ", "").replace("punto", ".").replace(" at ", "@").replace(" chiocciola ", "@")

    # Store email in state
    flow_manager.state["patient_email"] = email

    logger.info(f"📧 Patient email collected: {email}")

    from flows.nodes.patient_details import create_confirm_email_node
    return {
        "success": True,
        "email": email,
        "message": "Email collected successfully"
    }, create_confirm_email_node(email)


async def confirm_email_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Confirm email address and transition directly to reminder authorization (skip bulk verification)"""
    action = args.get("action", "")

    if action == "confirm":
        logger.info("✅ Email confirmed, generating fiscal code and proceeding to reminder authorization")

        # STT SWITCHING DISABLED FOR TESTING - keep using Nova-2
        # from utils.stt_switcher import switch_to_default_transcription
        # await switch_to_default_transcription()

        # Generate fiscal code from collected data
        await generate_fiscal_code_from_state(flow_manager)

        # Go directly to reminder authorization (skip bulk verification)
        from flows.nodes.patient_details import create_collect_reminder_authorization_node
        return {
            "success": True,
            "message": "Email confirmed, fiscal code generated, proceeding to authorization questions"
        }, create_collect_reminder_authorization_node()

    elif action == "change":
        logger.info("🔄 Email needs to be changed, returning to email collection")
        # Keep Nova-3 mode active since we're staying in email collection

        from flows.nodes.patient_details import create_collect_email_node
        return {
            "success": False,
            "message": "Let's collect your email again"
        }, create_collect_email_node()

    else:
        return {"success": False, "message": "Please confirm if the email is correct or if you want to change it"}, None


async def generate_fiscal_code_from_state(flow_manager: FlowManager) -> None:
    """Generate fiscal code from collected patient data in state"""
    try:
        # Extract patient data from state - check both individual keys and patient_data dict
        patient_data_dict = flow_manager.state.get("patient_data", {})

        patient_data = {
            'name': flow_manager.state.get("patient_name", ""),
            'surname': flow_manager.state.get("patient_surname", ""),
            'birth_date': flow_manager.state.get("patient_dob", patient_data_dict.get("date_of_birth", "")),
            'gender': flow_manager.state.get("patient_gender", patient_data_dict.get("gender", "")),
            'birth_city': flow_manager.state.get("patient_birth_city", patient_data_dict.get("birth_city", ""))
        }

        logger.info(f"🔧 Generating fiscal code from state data: {patient_data}")

        # Generate fiscal code
        result = fiscal_code_generator.generate_fiscal_code(patient_data)

        if result["success"]:
            fiscal_code = result["fiscal_code"]
            flow_manager.state["generated_fiscal_code"] = fiscal_code
            flow_manager.state["fiscal_code_generation_data"] = result

            logger.success(f"✅ Fiscal code generated and stored: {fiscal_code}")
            logger.info(f"📍 Matched city: {result.get('matched_city')} "
                       f"(similarity: {result.get('similarity_score')}%)")
        else:
            error_msg = result.get("error", "Unknown error")
            logger.error(f"❌ Fiscal code generation failed: {error_msg}")

            # Store error for potential debugging
            flow_manager.state["fiscal_code_error"] = error_msg
            if "suggestions" in result:
                flow_manager.state["city_suggestions"] = result["suggestions"]

    except Exception as e:
        logger.error(f"❌ Error in fiscal code generation: {e}")
        flow_manager.state["fiscal_code_error"] = str(e)



async def collect_reminder_authorization_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Collect reminder authorization and transition to marketing authorization"""
    reminder_auth = args.get("reminder_authorization", False)

    # Store reminder authorization in state
    flow_manager.state["reminder_authorization"] = reminder_auth

    logger.info(f"📧 Reminder authorization: {'Yes' if reminder_auth else 'No'}")

    from flows.nodes.patient_details import create_collect_marketing_authorization_node
    return {
        "success": True,
        "reminder_authorization": reminder_auth,
        "message": "Reminder preference collected"
    }, create_collect_marketing_authorization_node()


async def collect_marketing_authorization_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Collect marketing authorization and proceed directly to booking completion"""
    marketing_auth = args.get("marketing_authorization", False)

    # COMPREHENSIVE DEBUG LOGGING FOR FINAL STEP
    logger.info("🔍 DEBUG: === MARKETING AUTHORIZATION HANDLER ===")
    logger.info(f"🔍 DEBUG: Args received: {args}")
    logger.info(f"🔍 DEBUG: marketing_auth = {marketing_auth}")

    # Store marketing authorization in state
    flow_manager.state["marketing_authorization"] = marketing_auth

    logger.info(f"📢 Marketing authorization: {'Yes' if marketing_auth else 'No'}")
    logger.info("✅ All patient details collected, proceeding directly to final booking")

    # Log current state before final booking
    logger.info(f"🔍 DEBUG: State keys before final booking: {list(flow_manager.state.keys())}")
    logger.info(f"🔍 DEBUG: selected_slot exists: {'selected_slot' in flow_manager.state}")
    logger.info(f"🔍 DEBUG: booked_slots exists: {'booked_slots' in flow_manager.state}")

    # Skip bulk verification - proceed directly to booking creation
    logger.info("🔍 DEBUG: Calling confirm_details_and_create_booking...")
    try:
        result = await confirm_details_and_create_booking({"details_confirmed": True}, flow_manager)
        logger.info(f"🔍 DEBUG: confirm_details_and_create_booking returned: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ DEBUG: Exception in confirm_details_and_create_booking: {e}")
        raise


async def confirm_details_and_create_booking(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Confirm patient details and create final booking"""
    details_confirmed = args.get("details_confirmed", False)

    if not details_confirmed:
        # If details not confirmed, restart name collection
        logger.info("🔄 Patient details not confirmed, restarting collection")
        from flows.nodes.patient_details import create_collect_name_node
        return {
            "success": False,
            "message": "Let's collect your details again"
        }, create_collect_name_node()

    logger.info("✅ Patient details confirmed, proceeding to final booking")

    # COMPREHENSIVE DEBUG LOGGING - Track exactly what we have in state
    logger.info("🔍 DEBUG: Starting booking data validation")
    logger.info(f"🔍 DEBUG: Complete flow_manager.state keys: {list(flow_manager.state.keys())}")

    # Get all required data from state
    selected_services = flow_manager.state.get("selected_services", [])
    booked_slots = flow_manager.state.get("booked_slots", [])

    logger.info(f"🔍 DEBUG: selected_services = {selected_services}")
    logger.info(f"🔍 DEBUG: selected_services type = {type(selected_services)}")
    logger.info(f"🔍 DEBUG: selected_services length = {len(selected_services) if selected_services else 'None'}")

    logger.info(f"🔍 DEBUG: booked_slots = {booked_slots}")
    logger.info(f"🔍 DEBUG: booked_slots type = {type(booked_slots)}")
    logger.info(f"🔍 DEBUG: booked_slots length = {len(booked_slots) if booked_slots else 'None'}")

    # Check if selected_slot exists
    selected_slot_exists = "selected_slot" in flow_manager.state
    selected_slot_value = flow_manager.state.get("selected_slot", "NOT_FOUND")
    logger.info(f"🔍 DEBUG: selected_slot exists? {selected_slot_exists}")
    logger.info(f"🔍 DEBUG: selected_slot value = {selected_slot_value}")

    # If booked_slots is empty but we have selected_slot, this is a CRITICAL ERROR
    # The slot should have been reserved via create_slot() API in select_slot_and_book()
    if not booked_slots and "selected_slot" in flow_manager.state:
        logger.error("❌ CRITICAL ERROR: booked_slots is empty but selected_slot exists!")
        logger.error("❌ This means slot reservation (create_slot API) was skipped or failed!")
        selected_slot = flow_manager.state["selected_slot"]
        logger.error(f"❌ selected_slot data = {selected_slot}")

        # This should NOT happen in the fixed flow, but provide fallback with clear error
        logger.error("❌ FALLBACK: Cannot create valid booking without reserved slot UUID")
        logger.error("❌ The providing_entity_availability_uuid cannot be used for final booking")

        from flows.nodes.completion import create_error_node
        return {
            "success": False,
            "message": "Slot reservation failed - cannot complete booking"
        }, create_error_node("Slot reservation failed. The time slot was not properly reserved. Please start the booking process again.")
    else:
        if booked_slots:
            logger.info(f"🔍 DEBUG: booked_slots already exists: {booked_slots}")
        if not selected_slot_exists:
            logger.error("❌ DEBUG: No selected_slot found in state - this is a problem!")

    # Get patient data with extensive logging
    patient_name = flow_manager.state.get("patient_name", "")
    patient_surname = flow_manager.state.get("patient_surname", "")
    patient_phone = flow_manager.state.get("patient_phone", "")
    patient_email = flow_manager.state.get("patient_email", "")
    patient_fiscal_code = flow_manager.state.get("generated_fiscal_code", "")

    logger.info(f"🔍 DEBUG: patient_name = '{patient_name}'")
    logger.info(f"🔍 DEBUG: patient_surname = '{patient_surname}'")
    logger.info(f"🔍 DEBUG: patient_phone = '{patient_phone}'")
    logger.info(f"🔍 DEBUG: patient_email = '{patient_email}'")
    logger.info(f"🔍 DEBUG: patient_fiscal_code = '{patient_fiscal_code}'")

    # Also check for patient data from test setup
    patient_data_dict = flow_manager.state.get("patient_data", {})
    patient_gender = flow_manager.state.get("patient_gender", patient_data_dict.get("gender", "m"))
    patient_dob = flow_manager.state.get("patient_dob", patient_data_dict.get("date_of_birth", ""))

    logger.info(f"🔍 DEBUG: patient_data_dict = {patient_data_dict}")
    logger.info(f"🔍 DEBUG: patient_gender = '{patient_gender}'")
    logger.info(f"🔍 DEBUG: patient_dob = '{patient_dob}'")

    reminder_auth = flow_manager.state.get("reminder_authorization", False)
    marketing_auth = flow_manager.state.get("marketing_authorization", False)

    logger.info(f"🔍 DEBUG: reminder_authorization = {reminder_auth}")
    logger.info(f"🔍 DEBUG: marketing_authorization = {marketing_auth}")

    # Detailed validation check
    validation_results = {
        "selected_services": bool(selected_services),
        "booked_slots": bool(booked_slots),
        "patient_name": bool(patient_name),
        "patient_surname": bool(patient_surname),
        "patient_phone": bool(patient_phone),
        "patient_email": bool(patient_email),
        "patient_fiscal_code": bool(patient_fiscal_code)
    }

    logger.info(f"🔍 DEBUG: Validation results: {validation_results}")

    missing_fields = [field for field, is_valid in validation_results.items() if not is_valid]
    if missing_fields:
        logger.error(f"❌ DEBUG: Missing required fields: {missing_fields}")

        # Log the specific values of missing fields
        for field in missing_fields:
            if field == "selected_services":
                logger.error(f"❌ {field}: {selected_services}")
            elif field == "booked_slots":
                logger.error(f"❌ {field}: {booked_slots}")
            elif field == "patient_name":
                logger.error(f"❌ {field}: '{patient_name}'")
            elif field == "patient_surname":
                logger.error(f"❌ {field}: '{patient_surname}'")
            elif field == "patient_phone":
                logger.error(f"❌ {field}: '{patient_phone}'")
            elif field == "patient_email":
                logger.error(f"❌ {field}: '{patient_email}'")
            elif field == "patient_fiscal_code":
                logger.error(f"❌ {field}: '{patient_fiscal_code}'")

    if not all([selected_services, booked_slots, patient_name, patient_surname,
                patient_phone, patient_email, patient_fiscal_code]):
        logger.error("❌ FINAL VALIDATION FAILED - Creating error node")
        from flows.nodes.completion import create_error_node
        return {
            "success": False,
            "message": "Missing required information for booking"
        }, create_error_node("Missing required information for booking. Please start over.")

    try:
        # Store booking parameters for processing node
        flow_manager.state["pending_booking_params"] = {
            "selected_services": selected_services,
            "booked_slots": booked_slots,
            "patient_name": patient_name,
            "patient_surname": patient_surname,
            "patient_phone": patient_phone,
            "patient_email": patient_email,
            "patient_fiscal_code": patient_fiscal_code,
            "patient_gender": patient_gender,
            "patient_dob": patient_dob,
            "reminder_auth": reminder_auth,
            "marketing_auth": marketing_auth
        }

        # Create intermediate node with pre_actions for immediate TTS
        booking_status_text = "Creazione della prenotazione con tutti i dettagli forniti. Attendi..."

        from flows.nodes.patient_details import create_booking_processing_node
        return {
            "success": True,
            "message": "Starting booking creation"
        }, create_booking_processing_node(booking_status_text)

    except Exception as e:
        logger.error(f"❌ Booking creation initialization error: {e}")
        from flows.nodes.completion import create_error_node
        return {
            "success": False,
            "message": "Booking creation failed. Please try again."
        }, create_error_node("Booking creation failed. Please try again.")


async def perform_booking_creation_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Perform the actual booking creation after TTS message"""
    try:
        # COMPREHENSIVE DEBUG LOGGING FOR BOOKING CREATION
        logger.info("🔍 DEBUG: === BOOKING CREATION STARTED ===")
        logger.info(f"🔍 DEBUG: Args received: {args}")

        # Get stored booking parameters
        params = flow_manager.state.get("pending_booking_params", {})
        logger.info(f"🔍 DEBUG: pending_booking_params exists: {bool(params)}")
        logger.info(f"🔍 DEBUG: pending_booking_params keys: {list(params.keys()) if params else 'EMPTY'}")

        if not params:
            logger.error("❌ DEBUG: No pending_booking_params found!")
            from flows.nodes.completion import create_error_node
            return {
                "success": False,
                "message": "Missing booking parameters"
            }, create_error_node("Missing booking parameters. Please start over.")

        # Extract parameters
        selected_services = params["selected_services"]
        booked_slots = params["booked_slots"]
        patient_name = params["patient_name"]
        patient_surname = params["patient_surname"]
        patient_phone = params["patient_phone"]
        patient_email = params["patient_email"]
        patient_fiscal_code = params["patient_fiscal_code"]
        patient_gender = params["patient_gender"]
        patient_dob = params["patient_dob"]
        reminder_auth = params["reminder_auth"]
        marketing_auth = params["marketing_auth"]

        logger.info(f"🔍 DEBUG: Extracted booking parameters:")
        logger.info(f"   - selected_services: {selected_services}")
        logger.info(f"   - booked_slots: {booked_slots}")
        logger.info(f"   - patient_name: '{patient_name}'")
        logger.info(f"   - patient_surname: '{patient_surname}'")
        logger.info(f"   - patient_phone: '{patient_phone}'")
        logger.info(f"   - patient_email: '{patient_email}'")
        logger.info(f"   - patient_fiscal_code: '{patient_fiscal_code}'")
        logger.info(f"   - patient_gender: '{patient_gender}'")
        logger.info(f"   - patient_dob: '{patient_dob}'")
        logger.info(f"   - reminder_auth: {reminder_auth}")
        logger.info(f"   - marketing_auth: {marketing_auth}")

        # Import and call booking service
        from services.booking_api import create_booking

        # Prepare booking data
        booking_data = {
            "patient": {
                "name": patient_name,
                "surname": patient_surname,
                "email": patient_email,
                "phone": patient_phone,
                "date_of_birth": patient_dob,
                "fiscal_code": patient_fiscal_code,
                "gender": patient_gender.upper()
            },
            "booking_type": "private",
            "health_services": [],
            "reminder_authorization": reminder_auth,
            "marketing_authorization": marketing_auth
        }

        # Add health services with their slot UUIDs
        for i, service in enumerate(selected_services):
            if i < len(booked_slots):
                booking_data["health_services"].append({
                    "uuid": service.uuid,
                    "slot": booked_slots[i]["slot_uuid"]
                })

        logger.info(f"📝 Creating final booking with data: {booking_data}")

        # Create the booking
        booking_response = create_booking(booking_data)

        if booking_response.get("success", False):
            # Store booking information
            flow_manager.state["final_booking"] = booking_response["booking"]

            logger.success(f"🎉 Booking created successfully: {booking_response['booking'].get('code', 'N/A')}")

            from flows.nodes.booking_completion import create_booking_success_final_node
            return {
                "success": True,
                "booking_code": booking_response["booking"].get("code", ""),
                "booking_uuid": booking_response["booking"].get("uuid", ""),
                "message": "Booking created successfully"
            }, create_booking_success_final_node(booking_response["booking"], selected_services, booked_slots)
        else:
            # Booking failed
            error_msg = booking_response.get("message", "Booking creation failed")
            logger.error(f"❌ Booking creation failed: {error_msg}")

            from flows.nodes.completion import create_error_node
            return {
                "success": False,
                "message": error_msg
            }, create_error_node(f"Booking creation failed: {error_msg}")

    except Exception as e:
        logger.error(f"Booking creation error: {e}")
        from flows.nodes.completion import create_error_node
        return {
            "success": False,
            "message": "Failed to create booking"
        }, create_error_node("Failed to create booking. Please try again.")