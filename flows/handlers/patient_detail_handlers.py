"""
Patient detail collection flow handlers
"""

from typing import Dict, Any, Tuple
from loguru import logger

from pipecat_flows import FlowManager, NodeConfig, FlowArgs
from services.fiscal_code_generator import fiscal_code_generator


async def start_email_collection_with_stt_switch(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Handler for starting email collection with STT switch - used when testing email node directly"""
    # Switch to email transcription mode
    from utils.stt_switcher import switch_to_email_transcription
    await switch_to_email_transcription()

    # Transition to email collection
    from flows.nodes.patient_details import create_collect_email_node
    return {
        "success": True,
        "message": "Starting email collection with Nova-3 transcription"
    }, create_collect_email_node()


async def collect_name_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Collect patient name and transition to surname collection"""
    name = args.get("name", "").strip()

    if not name or len(name) < 1:
        return {"success": False, "message": "Per favore fornisci il tuo nome"}, None

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
        return {"success": False, "message": "Per favore fornisci il tuo cognome"}, None

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
    """Collect patient phone and transition to email collection"""
    phone = args.get("phone", "").strip()

    if not phone or len(phone) < 8:
        return {"success": False, "message": "Please provide a valid phone number"}, None

    # Clean phone number (remove spaces, dashes, etc.)
    phone_clean = ''.join(filter(str.isdigit, phone))

    if len(phone_clean) < 8:
        return {"success": False, "message": "Please provide a valid phone number with at least 8 digits"}, None

    # Store phone in state
    flow_manager.state["patient_phone"] = phone_clean

    logger.info(f"📞 Patient phone collected: {phone_clean}")

    # Switch to email transcription mode before transitioning to email node
    from utils.stt_switcher import switch_to_email_transcription
    await switch_to_email_transcription()

    from flows.nodes.patient_details import create_collect_email_node
    return {
        "success": True,
        "phone": phone_clean,
        "message": "Phone number collected successfully"
    }, create_collect_email_node()


async def collect_email_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Collect patient email with enhanced validation and transition to fiscal code collection"""
    email = args.get("email", "").strip().lower()

    if not email or "@" not in email or "." not in email:
        return {"success": False, "message": "Per favore fornisci un indirizzo email valido. Assicurati di includere @ e un dominio."}, None

    # Enhanced email validation
    email_parts = email.split("@")
    if len(email_parts) != 2 or len(email_parts[0]) < 1 or len(email_parts[1]) < 3:
        return {"success": False, "message": "Formato email non valido. Per favore riprova con un email completa."}, None

    # Additional validation for common email patterns
    domain_part = email_parts[1]
    if "." not in domain_part or domain_part.startswith(".") or domain_part.endswith("."):
        return {"success": False, "message": "Il dominio dell'email non è valido. Per favore riprova."}, None

    # Clean up common speech-to-text errors
    email = email.replace(" ", "").replace("punto", ".").replace(" at ", "@").replace(" chiocciola ", "@")

    # Store email in state
    flow_manager.state["patient_email"] = email

    logger.info(f"📧 Patient email collected: {email}")

    from flows.nodes.patient_details import create_confirm_email_node
    return {
        "success": True,
        "email": email,
        "message": "Email raccolta con successo"
    }, create_confirm_email_node(email)


async def confirm_email_and_transition(args: FlowArgs, flow_manager: FlowManager) -> Tuple[Dict[str, Any], NodeConfig]:
    """Confirm email address and transition to reminder authorization (skip fiscal code collection)"""
    action = args.get("action", "")

    if action == "confirm":
        logger.info("✅ Email confirmed, generating fiscal code and proceeding to reminder authorization")

        # Switch back to default transcription mode after email is confirmed
        from utils.stt_switcher import switch_to_default_transcription
        await switch_to_default_transcription()

        # Generate fiscal code from collected data
        await generate_fiscal_code_from_state(flow_manager)

        from flows.nodes.patient_details import create_collect_reminder_authorization_node
        return {
            "success": True,
            "message": "Email confirmed, fiscal code generated"
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
        # Extract patient data from state
        patient_data = {
            'name': flow_manager.state.get("patient_name", ""),
            'surname': flow_manager.state.get("patient_surname", ""),
            'birth_date': flow_manager.state.get("patient_dob", ""),
            'gender': flow_manager.state.get("patient_gender", ""),
            'birth_city': flow_manager.state.get("patient_birth_city", "")
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
    """Collect marketing authorization and transition to details confirmation"""
    marketing_auth = args.get("marketing_authorization", False)

    # Store marketing authorization in state
    flow_manager.state["marketing_authorization"] = marketing_auth

    logger.info(f"📢 Marketing authorization: {'Yes' if marketing_auth else 'No'}")

    # Prepare patient details for confirmation (no fiscal code shown - it's generated silently)
    patient_details = {
        "name": flow_manager.state.get("patient_name", ""),
        "surname": flow_manager.state.get("patient_surname", ""),
        "phone": flow_manager.state.get("patient_phone", ""),
        "email": flow_manager.state.get("patient_email", "")
        # Note: fiscal_code is generated and stored but not shown to patient
    }

    from flows.nodes.patient_details import create_confirm_patient_details_node
    return {
        "success": True,
        "marketing_authorization": marketing_auth,
        "message": "Marketing preference collected"
    }, create_confirm_patient_details_node(patient_details)


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

    # Get all required data from state
    selected_services = flow_manager.state.get("selected_services", [])
    booked_slots = flow_manager.state.get("booked_slots", [])
    patient_name = flow_manager.state.get("patient_name", "")
    patient_surname = flow_manager.state.get("patient_surname", "")
    patient_phone = flow_manager.state.get("patient_phone", "")
    patient_email = flow_manager.state.get("patient_email", "")
    patient_fiscal_code = flow_manager.state.get("generated_fiscal_code", "")
    patient_gender = flow_manager.state.get("patient_gender", "m")
    patient_dob = flow_manager.state.get("patient_dob", "")
    reminder_auth = flow_manager.state.get("reminder_authorization", False)
    marketing_auth = flow_manager.state.get("marketing_authorization", False)

    if not all([selected_services, booked_slots, patient_name, patient_surname,
                patient_phone, patient_email, patient_fiscal_code]):
        from flows.nodes.completion import create_error_node
        return {
            "success": False,
            "message": "Missing required information for booking"
        }, create_error_node("Missing required information for booking. Please start over.")

    try:
        # Make agent speak during booking creation
        booking_status_text = "Creazione della prenotazione con tutti i dettagli forniti. Attendi..."

        from pipecat.frames.frames import TTSSpeakFrame
        if flow_manager.task:
            await flow_manager.task.queue_frames([TTSSpeakFrame(text=booking_status_text)])

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