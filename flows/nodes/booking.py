"""
Booking and appointment management nodes
"""

import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, Any, List
from pipecat_flows import NodeConfig, FlowsFunctionSchema

from models.requests import HealthService, HealthCenter
from flows.handlers.flow_handlers import generate_flow_and_transition, finalize_services_and_search_centers
from flows.handlers.booking_handlers import (
    search_final_centers_and_transition,
    select_center_and_book,
    check_cerba_membership_and_transition,
    collect_datetime_and_transition,
    search_slots_and_transition,
    select_slot_and_book,
    create_booking_and_transition,
    handle_booking_modification,
    confirm_booking_summary_and_proceed
)
from config.settings import settings


def create_orange_box_node() -> NodeConfig:
    """Create the Orange Box node that generates decision flows"""
    return NodeConfig(
        name="orange_box_flow_generation", 
        role_messages=[{
            "role": "system",
            "content": f"Generate decision flow based on the characteristics of the selected health service. {settings.language_config}"
        }],
        task_messages=[{
            "role": "system",
            "content": "Now I'll analyze the selected service to determine if there are special requirements or additional options. Please wait a moment."
        }],
        functions=[
            FlowsFunctionSchema(
                name="generate_flow",
                handler=generate_flow_and_transition,
                description="Generate decision flow for the selected service",
                properties={},
                required=[]
            )
        ],
        respond_immediately=True  # Automatically trigger flow generation
    )


def create_flow_navigation_node(generated_flow: dict, service_name: str) -> NodeConfig:
    """Create LLM-driven flow navigation node"""
    return NodeConfig(
        name="flow_navigation",
        role_messages=[{
            "role": "system",
            "content": f"""You are navigating a decision flow for the health service: {service_name}

FOLLOW THIS EXACT FLOW STRUCTURE: {json.dumps(generated_flow, indent=2)}

IMPORTANT INSTRUCTIONS:
1. Start with the main flow message
2. Present questions exactly as written in the flow
3. Follow yes/no branches based on user responses
4. When presenting service options, show ONLY service names from list_health_services - NEVER mention UUIDs
5. If list_health_services is empty in a question but contains services in response branches, show those services when asking the question
6. When user selects additional services, track them internally with their UUIDs
7. When user answers "yes" to specialist visit questions, include those specialist services
8. When reaching a final action (save_cart, etc.), call finalize_services function
9. CRITICAL: include ALL services chosen by user during conversation

**CRITICAL RULES:**
- NEVER mention UUIDs to users - they are internal only
- NEVER use 1, 2, 3 or numbers when presenting services
- List only service names separated by commas or line breaks, without numerical prefixes
- If a question is about services but list_health_services is empty, check response branches for available services to display

Flow decision logic:
- If user chooses additional services from main list, include those services
- If user answers YES to specialist visit questions, include specialist services from that branch
- If user answers NO, follow the "no" branch accordingly

FUNDAMENTAL: When asking questions about services:
- If current question has list_health_services with items, show those services
- If current question has empty list_health_services but "yes" or "no" branches contain list_health_services, show THOSE services in your question
- Example: question asks "Would you like a specialist consultation?" and "yes" branch has list_health_services: ["Cardiology Visit"], so say "Would you like to book a specialist visit? The available specialist visit is: Cardiology Visit"
- Always show only service names, never UUIDs, never numbers

Be conversational but follow the flow structure carefully. Always speak like a human, not a robot. {settings.language_config}"""
        }],
        task_messages=[{
            "role": "system",
            "content": f"Start the decision flow for {service_name}. Begin with the main message from the generated flow."
        }],
        functions=[
            FlowsFunctionSchema(
                name="finalize_services",
                handler=finalize_services_and_search_centers,
                description="Finalize ALL service selections (including specialist visits) and proceed to center search",
                properties={
                    "additional_services": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "uuid": {"type": "string", "description": "Service UUID from the flow structure"},
                                "name": {"type": "string", "description": "Service name from the flow structure"}
                            },
                            "required": ["uuid", "name"]
                        },
                        "description": "ALL additional services selected during flow navigation, including optional services AND specialist visits if user chose them"
                    },
                    "specialist_visit_chosen": {
                        "type": "boolean",
                        "description": "Whether the user chose to book a specialist visit"
                    },
                    "flow_path": {
                        "type": "string",
                        "description": "The path through the decision tree (e.g., 'yes->yes', 'yes->no')"
                    }
                },
                required=[]
            )
        ]
    )


def create_final_center_search_node() -> NodeConfig:
    """Create final center search node with all services"""
    return NodeConfig(
        name="final_center_search", 
        role_messages=[{
            "role": "system",
            "content": f"Search health centers that provide all selected services. {settings.language_config}"
        }],
        task_messages=[{
            "role": "system",
            "content": "Perfect! Now I'll search for health centers that can provide all selected services. Please wait a moment."
        }],
        functions=[
            FlowsFunctionSchema(
                name="search_final_centers",
                handler=search_final_centers_and_transition,
                description="Search health centers with all selected services",
                properties={},
                required=[]
            )
        ],
        respond_immediately=True  # Automatically trigger the search
    )


def create_final_center_selection_node(centers: List[HealthCenter], services: List[HealthService]) -> NodeConfig:
    """Create final center selection node with top 3 centers"""
    top_centers = centers[:3]
    center_options = "\n\n".join([f"**{center.name}** in {center.city}\nAddress: {center.address}" for center in top_centers])
    service_names = ", ".join([s.name for s in services])
    
    task_content = f"""Perfect! I found these health centers that can provide your services ({service_names}):

{center_options}

Which health center would you prefer for your appointment? Just tell me the name or number."""
    
    return NodeConfig(
        name="final_center_selection",
        role_messages=[{
            "role": "system",
            "content": f"""You are helping a patient choose between {len(top_centers)} health centers that can provide their services: {service_names}.

IMPORTANT: You must clearly present the health centers and ask the patient to choose one. Never say generic phrases like "complete the booking" - instead, present the specific centers and ask them to choose.

When the patient selects a center, call the select_center function with the correct center UUID.

Available centers:
{chr(10).join([f"- {center.name} (UUID: {center.uuid})" for center in top_centers])}

CRITICAL: When speaking to users, only mention the full centers name (e.g., "Milano Via Emilio de Marchi 4 - Biochimico, Cologno Monzese Viale Liguria 37 - Curie, ozzano Viale Toscana 35/37 - Delta Medica"). NEVER read full addresses or detailed information aloud.

Always speak naturally like a human. {settings.language_config}"""
        }],
        task_messages=[{
            "role": "system",
            "content": task_content
        }],
        functions=[
            FlowsFunctionSchema(
                name="select_center",
                handler=select_center_and_book,
                description="Select a health center for booking",
                properties={
                    "center_uuid": {
                        "type": "string",
                        "description": "UUID of the selected health center"
                    }
                },
                required=["center_uuid"]
            )
        ]
    )


def create_no_centers_node(address: str, service_name: str) -> NodeConfig:
    """Dynamically create node when no centers are found"""
    return NodeConfig(
        name="no_centers_found",
        role_messages=[{
            "role": "system",
            "content": "Apologetically explain that no health centers were found and offer alternatives."
        }],
        task_messages=[{
            "role": "system",
            "content": f"No health center found at {address} for {service_name}. Apologize and ask if they'd like to try a different location or service. Offer to start over. {settings.language_config}"
        }],
        functions=[
            FlowsFunctionSchema(
                name="search_health_services",
                handler=lambda args, flow_manager: None,  # Import this properly in implementation
                description="Search for different health services",
                properties={
                    "search_term": {
                        "type": "string",
                        "description": "New service name to search for"
                    }
                },
                required=["search_term"]
            )
        ]
    )


def create_cerba_membership_node() -> NodeConfig:
    """Create Cerba membership check node"""
    return NodeConfig(
        name="cerba_membership_check",
        role_messages=[{
            "role": "system",
            "content": f"Ask the patient if he or she is a Cerba member to calculate prices. {settings.language_config}"
        }],
        task_messages=[{
            "role": "system",
            "content": "Do you have a Cerba Card?"
        }],
        functions=[
            FlowsFunctionSchema(
                name="check_cerba_membership",
                handler=check_cerba_membership_and_transition,
                description="Check if user is a Cerba member",
                properties={
                    "is_cerba_member": {
                        "type": "boolean",
                        "description": "Whether the user is a Cerba member (true/false)"
                    }
                },
                required=["is_cerba_member"]
            )
        ]
    )


def create_collect_datetime_node() -> NodeConfig:
    """Create date and time collection node"""
    return NodeConfig(
        name="collect_datetime",
        role_messages=[{
            "role": "system",
            "content": f"The current year is 2025. Collect the preferred date and optional time for the appointment. If the user says 'morning' or mentions morning time, prefer 8:00-12:00 (24-hour clock). If they say 'afternoon' or mention afternoon time, prefer 12:00-19:00 (24-hour clock). Always use and display the 24-hour clock (e.g., 1:40 PM, 3:30 PM) - NEVER convert to 12-hour clock. Internally convert the user's natural language date to YYY-MM-DD format. Be flexible with user input formats. Speak naturally like a human. {settings.language_config}"
        }],
        task_messages=[{
            "role": "system",
            "content": "What date and time would you prefer for your appointment?"
        }],
        functions=[
            FlowsFunctionSchema(
                name="collect_datetime",
                handler=collect_datetime_and_transition,
                description="Collect preferred appointment date and optional time preference",
                properties={
                    "preferred_date": {
                        "type": "string",
                        "description": "Preferred appointment date in YYYY-MM-DD format"
                    },
                    "preferred_time": {
                        "type": "string",
                        "description": "Preferred appointment time (specific time like '9:00', '14:30' or time range like 'morning', 'afternoon'')"
                    },
                    "time_preference": {
                        "type": "string",
                        "description": "Time preference: 'morning' (8:00-12:00), 'afternoon' (12:00-19:00), 'specific' (exact time), or 'any' (no preference)"
                    }
                },
                required=["preferred_date"]
            )
        ]
    )


def create_collect_datetime_node_for_service(service_name: str = None, is_multi_service: bool = False) -> NodeConfig:
    """Create date and time collection node, optionally for specific service"""
    if is_multi_service and service_name:
        task_content = f"What date and time would you prefer for your appointment? {service_name}? {settings.language_config}"
        node_name = f"collect_datetime_{service_name.lower().replace(' ', '_')}"
    else:
        task_content = f"What date and time would you prefer for your appointment? {settings.language_config}"
        node_name = "collect_datetime"
    
    return NodeConfig(
        name=node_name,
        role_messages=[{
            "role": "system",
            "content": f"Collect the preferred date and time for the appointment. Internally convert the user's natural language date/time into YYYY-MM-DD and 24-hour clock formats. Be flexible with user input formats. {settings.language_config}"
        }],
        task_messages=[{
            "role": "system",
            "content": task_content
        }],
        functions=[
            FlowsFunctionSchema(
                name="collect_datetime",
                handler=collect_datetime_and_transition,
                description="Collect preferred appointment date and time",
                properties={
                    "preferred_date": {
                        "type": "string",
                        "description": "Preferred appointment date in YYYY-MM-DD format"
                    },
                    "preferred_time": {
                        "type": "string",
                        "description": "Preferred appointment time (e.g., '9:00', '14:30')"
                    }
                },
                required=["preferred_date", "preferred_time"]
            )
        ]
    )


def create_slot_search_node() -> NodeConfig:
    """Create automatic slot search node"""
    return NodeConfig(
        name="slot_search",
        role_messages=[{
            "role": "system",
            "content": f"Search for available appointment slots for the selected service and time. {settings.language_config}"
        }],
        task_messages=[{
            "role": "system",
            "content": "Let me search for available appointment slots for your preferred date and time. Please wait a moment..."
        }],
        functions=[
            FlowsFunctionSchema(
                name="search_slots",
                handler=search_slots_and_transition,
                description="Search for available appointment slots",
                properties={},
                required=[]
            )
        ],
        respond_immediately=True  # Automatically trigger slot search
    )


def create_slot_selection_node(slots: List[Dict], service: HealthService, is_cerba_member: bool = False) -> NodeConfig:
    """Create slot selection node with human-friendly slot parsing and presentation"""
    
    # Parse and group slots by date
    slots_by_date = {}
    parsed_slots = []

    # Debug: Log the first few raw slots to understand what we're working with
    if slots:
        from loguru import logger
        logger.debug(f"🔧 Processing {len(slots)} raw slots for {service.name}")
        for i, slot in enumerate(slots[:3]):
            start_time = slot.get('start_time', 'N/A')
            logger.debug(f"   Slot {i+1}: {start_time} -> UUID: {slot.get('providing_entity_availability_uuid', 'N/A')}")

    for slot in slots:
        # Convert UTC slot times to Italian local time for user display
        from services.timezone_utils import utc_to_italian_display, format_time_for_display

        italian_start = utc_to_italian_display(slot["start_time"])
        italian_end = utc_to_italian_display(slot["end_time"])

        # Fallback to original if conversion fails
        if not italian_start or not italian_end:
            logger.warning(f"⚠️ Timezone conversion failed, using original times")
            start_time_str = slot["start_time"].replace("T", " ").replace("+00:00", "")
            end_time_str = slot["end_time"].replace("T", " ").replace("+00:00", "")
            start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
        else:
            # Use converted Italian times
            start_dt = datetime.strptime(italian_start, "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.strptime(italian_end, "%Y-%m-%d %H:%M:%S")

        date_key = start_dt.strftime("%Y-%m-%d")
        formatted_date = start_dt.strftime("%d %B")

        # Format times in 24-hour format without leading zeros (Italian local time)
        start_time_24h = start_dt.strftime("%-H:%M")
        end_time_24h = end_dt.strftime("%-H:%M")
        
        parsed_slot = {
            'original': slot,
            'date_key': date_key,
            'formatted_date': formatted_date,
            'start_time_24h': start_time_24h,
            'end_time_24h': end_time_24h,
            'start_dt': start_dt,
            'end_dt': end_dt,
            'providing_entity_availability_uuid': slot.get('providing_entity_availability_uuid', ''),
            'health_center_name': slot.get('health_center', {}).get('name', ''),
            'service_name': slot.get('health_services', [{}])[0].get('name', service.name)
        }
        
        parsed_slots.append(parsed_slot)
        
        if date_key not in slots_by_date:
            slots_by_date[date_key] = []
        slots_by_date[date_key].append(parsed_slot)
    
    # Create human-like presentation with natural language
    if len(slots_by_date) == 1:
        # Same day - show available time slots in a conversational way
        date_key, day_slots = list(slots_by_date.items())[0]
        formatted_date = day_slots[0]['formatted_date']
        
        # Group by morning/afternoon for better presentation
        morning_slots = [s for s in day_slots if s['start_dt'].hour < 12]
        afternoon_slots = [s for s in day_slots if s['start_dt'].hour >= 12]
        
        # Create natural language slot presentation
        if len(day_slots) == 1:
            # Single slot - be very specific and natural
            slot = day_slots[0]
            task_content = f"Great! We have one slot available for {service.name} on {formatted_date} from {slot['start_time_24h']} to {slot['end_time_24h']}. Would you like me to book this appointment for you at {slot['start_time_24h']}?"
        elif len(day_slots) <= 6:
            # Few slots - show them in a natural way
            if afternoon_slots and not morning_slots:
                # Only afternoon slots
                first_slot = afternoon_slots[0]
                last_slot = afternoon_slots[-1] if len(afternoon_slots) > 1 else first_slot
                task_content = f"We have appointments available for {service.name} in the afternoon on {formatted_date} from {first_slot['start_time_24h']} to {last_slot['end_time_24h']}. What time would work best for you? I can book you at {first_slot['start_time_24h']} or any other available time."
            elif morning_slots and not afternoon_slots:
                # Only morning slots
                first_slot = morning_slots[0]
                last_slot = morning_slots[-1] if len(morning_slots) > 1 else first_slot
                task_content = f"We have appointments available for {service.name} in the morning on {formatted_date} from {first_slot['start_time_24h']} to {last_slot['end_time_24h']}. What time would work best for you? I can book you at {first_slot['start_time_24h']} or any other available time."
            else:
                # Both morning and afternoon
                morning_first = morning_slots[0]['start_time_24h'] if morning_slots else None
                afternoon_first = afternoon_slots[0]['start_time_24h'] if afternoon_slots else None
                if morning_first and afternoon_first:
                    task_content = f"We have appointments available for {service.name} on {formatted_date}. I can book you in the morning starting from {morning_first} or in the afternoon starting from {afternoon_first}. Which time preference would work better for you?"
                else:
                    first_slot = day_slots[0]
                    task_content = f"We have appointments available for {service.name} on {formatted_date}. The earliest available time is at {first_slot['start_time_24h']}. Should I book this time for you or would you prefer a different time?"
        else:
            # Many slots - group and be natural
            availability_text = f"We have several appointments available for {service.name} on {formatted_date}:\n\n"
            
            if morning_slots:
                morning_times = [f"{s['start_time_24h']} to {s['end_time_24h']}" for s in morning_slots[:3]]
                availability_text += f"Morning times: {', '.join(morning_times)}\n"
            
            if afternoon_slots:
                afternoon_times = [f"{s['start_time_24h']} to {s['end_time_24h']}" for s in afternoon_slots[:3]]
                availability_text += f"Afternoon times: {', '.join(afternoon_times)}\n"
            
            task_content = f"{availability_text}\nWhat time works best for you? Just tell me your preferred time and I'll book it for you."
        
    else:
        # Multiple days - show available dates and suggest choosing one
        available_dates = []
        for date_key in sorted(slots_by_date.keys())[:3]:  # Show max 3 dates
            day_slots = slots_by_date[date_key]
            formatted_date = day_slots[0]['formatted_date']
            slots_count = len(day_slots)
            available_dates.append(f"{formatted_date} ({slots_count} slots available)")
        
        dates_text = "\n- ".join(available_dates)
        task_content = f"We have appointments available on these dates:\n\n- {dates_text}\n\nWhich date would you prefer? Then I'll show you the available times for that day."
    
    # Create the slot selection context with all required booking info
    slot_context = {
        'parsed_slots': parsed_slots,
        'service_name': service.name,
        'available_slots_count': len(slots)
    }
    
    return NodeConfig(
        name="slot_selection",
        role_messages=[{
            "role": "system",
            "content": f"""It's currently 2025. Help the patient select from available appointment slots for {service.name}.

You have {len(slots)} available slots. When presenting slots:
- ALWAYS use 24-hour time format (e.g., 13:40, 15:30) - NEVER convert to 12-hour format
- CRITICAL: ONLY present times that actually exist in the available slots - DO NOT mention any times that aren't available
- IMPORTANT: When speaking times aloud, always say them in words never digits:
  * Italian: "nove e zero" for 9:00, "nove e quindici" for 9:15, "tredici e quaranta" for 13:40, "dodici e quarantacinque" for 12:45
  * English: "nine o'clock" for 9:00, "nine fifteen" for 9:15, "thirteen forty" for 13:40, "twelve forty-five" for 12:45

- IMPORTANT: When calling function, always use digits never use words:
  * Italian:  9:00 for "nove e zero" , 9:15 for "nove e quindici" , 13:40 for "tredici e quaranta" , 12:45 for "dodici e quarantacinque" 
  * English:  9:00 for "nine o'clock" , 9:15 for "nine fifteen" ,  13:40" for thirteen forty" , 12:45 for "twelve forty-five" 

- Never mention prices, UUIDs, or technical details
- Be conversational and human
- IMPORTANT: Before suggesting any time, verify it exists in the available slots list

Available slot data: {slot_context} {settings.language_config}"""
        }],
        task_messages=[{
            "role": "system",
            "content": task_content
        }],
        functions=[
            FlowsFunctionSchema(
                name="select_slot",
                handler=select_slot_and_book,
                description="Select a specific appointment slot by providing the slot UUID",
                properties={
                    "providing_entity_availability_uuid": {
                        "type": "string",
                        "description": "UUID of the providing entity availability for the selected slot"
                    },
                    "selected_time": {
                        "type": "string",
                        "description": "Readable time of the selected slot (e.g., '09:30 - 10:00')"
                    },
                    "selected_date": {
                        "type": "string",
                        "description": "Readable date of the selected slot (e.g., '21 November 2025')"
                    }
                },
                required=["providing_entity_availability_uuid"]
            )
        ]
    )


def create_booking_creation_node() -> NodeConfig:
    """Create booking confirmation and creation node"""
    return NodeConfig(
        name="booking_creation",
        role_messages=[{
            "role": "system",
            "content": f"Confirm booking details and create the appointment. {settings.language_config}"
        }],
        task_messages=[{
            "role": "system",
            "content": "Perfect! I'm ready to book your appointment. Please confirm if you want to proceed with this booking."
        }],
        functions=[
            FlowsFunctionSchema(
                name="create_booking",
                handler=create_booking_and_transition,
                description="Create the appointment booking",
                properties={
                    "confirm_booking": {
                        "type": "boolean",
                        "description": "Confirmation to proceed with booking (true/false)"
                    }
                },
                required=["confirm_booking"]
            )
        ]
    )


def create_slot_refresh_node(service_name: str) -> NodeConfig:
    """Create slot refresh node when booking fails due to unavailability"""
    return NodeConfig(
        name="slot_refresh",
        role_messages=[{
            "role": "system",
            "content": f"The selected slot for {service_name} is no longer available. Search for new available slots and present them to the patient. Be apologetic and helpful. {settings.language_config}"
        }],
        task_messages=[{
            "role": "system",
            "content": f"I apologize, but that time slot for {service_name} was just booked by someone else. Let me search for other available times for you."
        }],
        functions=[
            FlowsFunctionSchema(
                name="search_slots",
                handler=search_slots_and_transition,
                description="Search for updated available slots",
                properties={},
                required=[]
            )
        ],
        respond_immediately=True  # Automatically trigger slot search
    )


def create_no_slots_node(date: str, time_preference: str = "any time") -> NodeConfig:
    """Create node when no slots are available - with human-like alternative suggestions"""
    if time_preference == "any time":
        no_slots_message = f"I'm sorry, there are no available slots for {date}. I'd like to suggest some alternatives: would you like to try a different date? I can also check if there are available slots on nearby dates, for example a few days before or after."
    else:
        no_slots_message = f"I'm sorry, there are no available slots for {date} for {time_preference}. I'd like to suggest some alternatives: would you like to try a different date or time? For example, we might have available slots for {date} at a different time or on another date."
    
    return NodeConfig(
        name="no_slots_available",
        role_messages=[{
            "role": "system",
            "content": f"We are in 2025. When there are no available slots, be helpful and suggest alternatives in a human way. Offer to search for different dates or times. Never mention technical details or UUIDs. {settings.language_config}"
        }],
        task_messages=[{
            "role": "system",
            "content": no_slots_message
        }],
        functions=[
            FlowsFunctionSchema(
                name="collect_datetime",
                handler=collect_datetime_and_transition,
                description="Collect new preferred date and optional time preference",
                properties={
                    "preferred_date": {
                        "type": "string",
                        "description": "New preferred appointment date in YYYY-MM-DD format"
                    },
                    "preferred_time": {
                        "type": "string",
                        "description": "New preferred appointment time (specific time like '09:00', '14:30' or time range like 'morning', 'afternoon')"
                    },
                    "time_preference": {
                        "type": "string",
                        "description": "Time preference: 'morning' (8:00-12:00), 'afternoon' (12:00-19:00), 'specific' (exact time) or 'any' (no preference)"
                    }
                },
                required=["preferred_date"]
            )
        ]
    )


def _extract_clean_center_name(center_name: str) -> str:
    """Extract clean center name from full name that contains address info"""
    # Center names come in format: "City Address - Brand Name"
    # Example: "Rozzano Viale Toscana 35/37 - Delta Medica"
    # We want to extract just: "Delta Medica" or "City - Brand Name"

    if " - " in center_name:
        # Split by " - " and take the brand name part
        parts = center_name.split(" - ")
        if len(parts) >= 2:
            # Return the last part (brand name)
            return parts[-1].strip()

    # Fallback: return the original name
    return center_name


def create_booking_summary_confirmation_node(selected_services: List[HealthService], selected_slots: List[Dict], selected_center: HealthCenter, total_cost: float, is_cerba_member: bool = False) -> NodeConfig:
    """Create booking summary confirmation node with all details before personal info collection"""

    # Extract clean center name
    clean_center_name = _extract_clean_center_name(selected_center.name)

    # Format service details
    services_text = []
    for i, service in enumerate(selected_services):
        if i < len(selected_slots):
            slot = selected_slots[i]
            # Convert UTC slot times to Italian local time for user display
            from services.timezone_utils import utc_to_italian_display

            italian_start = utc_to_italian_display(slot["start_time"])
            italian_end = utc_to_italian_display(slot["end_time"])

            # Fallback to original if conversion fails
            if not italian_start or not italian_end:
                logger.warning(f"⚠️ Timezone conversion failed for booking summary, using original times")
                start_time_str = slot["start_time"].replace("T", " ").replace("+00:00", "")
                end_time_str = slot["end_time"].replace("T", " ").replace("+00:00", "")
                start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
            else:
                # Use converted Italian times
                start_dt = datetime.strptime(italian_start, "%Y-%m-%d %H:%M:%S")
                end_dt = datetime.strptime(italian_end, "%Y-%m-%d %H:%M:%S")

            formatted_date = start_dt.strftime("%d %B %Y")
            formatted_time = start_dt.strftime("%-H:%M")

            # Get the actual service price from the slot's health_services data
            service_cost = slot.get('price', 0)
            if service_cost == 0 and 'health_services' in slot and len(slot['health_services']) > 0:
                # Try to get price from health_services within the slot
                health_service = slot['health_services'][0]
                if is_cerba_member:
                    service_cost = health_service.get('cerba_card_price', health_service.get('price', 0))
                else:
                    service_cost = health_service.get('price', 0)

            services_text.append(f"• {service.name} il {formatted_date} alle {formatted_time} - {int(service_cost)} euro")

    services_summary = "\n".join(services_text)

    # Create summary content
    membership_text = " (with Cerba Card discount)" if is_cerba_member else ""

    summary_content = f"""Here's a summary of your booking:

**Services:**
{services_summary}

**Health Center:**
{clean_center_name}
{selected_center.address}

**Total Cost:** {int(total_cost)} euro{membership_text}

Would you like to proceed with this booking? If yes, I'll just need to collect some personal information to complete your appointment. If the cost is too high or you'd like to change anything, just let me know."""

    return NodeConfig(
        name="booking_summary_confirmation",
        role_messages=[{
            "role": "system",
            "content": f"CRITICAL: You must present EXACTLY the booking summary provided below. DO NOT change, modify, or hallucinate any times, dates, services, or prices. Use ONLY the exact information from the summary content. DO NOT mention any times other than what is explicitly written in the summary. This is just a summary - the actual booking will be created after collecting personal details. Ask for confirmation before proceeding to personal information collection. If the patient wants to cancel or change something, be helpful and offer alternatives. {settings.language_config}"
        }],
        task_messages=[{
            "role": "system",
            "content": summary_content
        }],
        functions=[
            FlowsFunctionSchema(
                name="confirm_booking_summary",
                handler=confirm_booking_summary_and_proceed,
                description="Confirm the booking summary and proceed to personal info collection or handle changes",
                properties={
                    "action": {
                        "type": "string",
                        "enum": ["proceed", "cancel", "change"],
                        "description": "proceed to continue with booking, cancel to stop, change to modify booking"
                    }
                },
                required=["action"]
            )
        ]
    )

def create_center_search_processing_node(address: str, tts_message: str) -> NodeConfig:
    """Create a processing node that speaks immediately before performing center search"""
    from flows.handlers.booking_handlers import perform_center_search_and_transition

    return NodeConfig(
        name="center_search_processing",
        pre_actions=[
            {
                "type": "tts_say",
                "text": tts_message
            }
        ],
        role_messages=[{
            "role": "system",
            "content": f"You are processing health center search in {address}. Immediately call perform_center_search to execute the actual search. {settings.language_config}"
        }],
        task_messages=[{
            "role": "system",
            "content": f"Now searching for health centers in {address} that provide all selected services. Please wait."
        }],
        functions=[
            FlowsFunctionSchema(
                name="perform_center_search",
                handler=perform_center_search_and_transition,
                description="Execute the actual center search after TTS message",
                properties={},
                required=[]
            )
        ]
    )


def create_slot_search_processing_node(service_name: str, tts_message: str) -> NodeConfig:
    """Create a processing node that speaks immediately before performing slot search"""
    from flows.handlers.booking_handlers import perform_slot_search_and_transition

    return NodeConfig(
        name="slot_search_processing",
        pre_actions=[
            {
                "type": "tts_say",
                "text": tts_message
            }
        ],
        role_messages=[{
            "role": "system",
            "content": f"You are processing slot search for {service_name}. Immediately call perform_slot_search to execute the actual search. {settings.language_config}"
        }],
        task_messages=[{
            "role": "system",
            "content": f"Now searching for available appointment slots for {service_name}. Please wait."
        }],
        functions=[
            FlowsFunctionSchema(
                name="perform_slot_search",
                handler=perform_slot_search_and_transition,
                description="Execute the actual slot search after TTS message",
                properties={},
                required=[]
            )
        ]
    )


def create_slot_booking_processing_node(service_name: str, tts_message: str) -> NodeConfig:
    """Create a processing node that speaks immediately before performing slot booking"""
    from flows.handlers.booking_handlers import perform_slot_booking_and_transition

    return NodeConfig(
        name="slot_booking_processing",
        pre_actions=[
            {
                "type": "tts_say",
                "text": tts_message
            }
        ],
        role_messages=[{
            "role": "system",
            "content": f"You are processing slot booking for {service_name}. Immediately call perform_slot_booking to execute the actual booking. {settings.language_config}"
        }],
        task_messages=[{
            "role": "system",
            "content": f"Now booking the selected time slot for {service_name}. Please wait for confirmation."
        }],
        functions=[
            FlowsFunctionSchema(
                name="perform_slot_booking",
                handler=perform_slot_booking_and_transition,
                description="Execute the actual slot booking after TTS message",
                properties={},
                required=[]
            )
        ]
    )
