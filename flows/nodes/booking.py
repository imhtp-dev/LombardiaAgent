"""
Booking and appointment management nodes
"""

import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, Any, List
from pipecat_flows import NodeConfig, FlowsFunctionSchema
from loguru import logger

from models.requests import HealthService, HealthCenter

# Global variable to store current session's filtered slots for UUID lookup
_current_session_slots = {}
from flows.handlers.flow_handlers import generate_flow_and_transition, finalize_services_and_search_centers
from flows.handlers.booking_handlers import (
    search_final_centers_and_transition,
    select_center_and_book,
    check_cerba_membership_and_transition,
    collect_datetime_and_transition,
    search_slots_and_transition,
    select_slot_and_book,
    create_booking_and_transition,
    confirm_booking_summary_and_proceed,
    update_date_and_search_slots
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
    service_names = ", ".join([s.name for s in services])

    # Create paragraph-style listing of health centers
    if len(top_centers) == 1:
        centers_text = f"The available health center is {top_centers[0].name}."
    elif len(top_centers) == 2:
        centers_text = f"The first one is {top_centers[0].name}, and the second is {top_centers[1].name}."
    elif len(top_centers) == 3:
        centers_text = f"The first one is {top_centers[0].name}, the second is {top_centers[1].name}, and the third is {top_centers[2].name}."
    else:
        # Fallback for more than 3 centers
        centers_list = [f"the {'first' if i == 0 else 'second' if i == 1 else 'third' if i == 2 else str(i+1)+'th'} one is {center.name}" for i, center in enumerate(top_centers)]
        centers_text = ", ".join(centers_list[:-1]) + f", and {centers_list[-1]}."

    task_content = f"""Here are some health centers that offer {service_names}. {centers_text}

Which one would you like to choose for your appointment?"""
    
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
    """Create date and time collection node with LLM-driven natural language support"""
    from datetime import datetime

    # Get today's complete date information for LLM context
    today = datetime.now()
    today_date = today.strftime("%Y-%m-%d")
    today_day = today.strftime("%A")  # Full day name (e.g., "Thursday")
    today_formatted = today.strftime("%B %d, %Y")  # e.g., "October 16, 2025"

    return NodeConfig(
        name="collect_datetime",
        role_messages=[{
            "role": "system",
            "content": f"""Today is {today_day}, {today_formatted} (date: {today_date}). The current year is 2025.

You can understand natural language date expressions and calculate the correct dates automatically. When a patient mentions expressions like:
- "tomorrow" → calculate the next day
- "next Friday" → calculate the next Friday from today
- "next week" → calculate 7 days from today
- "next month" → calculate approximately 30 days from today
- "next Thursday" → calculate the next Thursday (if today is Thursday, it means the following Thursday)

IMPORTANT:
- If the user says 'morning' or mentions morning time, set time_preference to "morning" (8:00-12:00)
- If they say 'afternoon' or mention afternoon time, set time_preference to "afternoon" (12:00-19:00)
- If they mention a specific time, set time_preference to "specific"
- If no time preference mentioned, set time_preference to "any"

Calculate the exact date in YYYY-MM-DD format and call the collect_datetime function directly.

Always use 24-hour time format. Be flexible with user input formats. Speak naturally like a human. {settings.language_config}"""
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
                        "description": "Preferred appointment date in YYYY-MM-DD format. Calculate from natural language expressions using today's date context. Examples: if today is 2025-10-16 (Thursday) and user says 'next Friday' → '2025-10-24', 'tomorrow' → '2025-10-17', 'next Thursday' → '2025-10-23'"
                    },
                    "preferred_time": {
                        "type": "string",
                        "description": "Preferred appointment time (specific time like '9:00', '14:30' or time range like 'morning', 'afternoon')"
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
                        "description": "Preferred appointment date in YYYY-MM-DD format. If user doesn't specify year, assume current year (2025). Examples: '24 November' → '2025-11-24', 'December 15' → '2025-12-15'"
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


def create_slot_selection_node(slots: List[Dict], service: HealthService, is_cerba_member: bool = False, user_preferred_date: str = None, time_preference: str = "any time") -> NodeConfig:
    """Create slot selection node with progressive filtering and minimal LLM data"""

    from loguru import logger

    # Parse and group slots by date
    slots_by_date = {}
    parsed_slots = []

    logger.info(f"🔧 SMART FILTERING: Processing {len(slots)} raw slots for {service.name}")
    logger.info(f"🔧 User preferred date: {user_preferred_date}")
    logger.info(f"🔧 Time preference: {time_preference}")

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

    logger.info(f"🔧 PARSED: Found slots for {len(slots_by_date)} different dates: {list(slots_by_date.keys())}")

    # PROGRESSIVE FILTERING LOGIC
    def filter_slots_by_time_preference(day_slots, preference):
        """Filter slots by morning (8-12) or afternoon (12-19)"""
        if preference == "morning":
            return [slot for slot in day_slots if 8 <= slot['start_dt'].hour < 12]
        elif preference == "afternoon":
            return [slot for slot in day_slots if 12 <= slot['start_dt'].hour < 19]
        else:
            return day_slots  # No time preference

    # Step 1: Check if user's preferred date has slots
    selected_slots_for_llm = []
    task_content = ""

    if user_preferred_date and user_preferred_date in slots_by_date:
        logger.info(f"✅ SMART FILTERING: User's preferred date {user_preferred_date} has slots!")
        day_slots = slots_by_date[user_preferred_date]

        # Step 2: Apply time preference filtering
        if time_preference in ["morning", "afternoon"]:
            filtered_slots = filter_slots_by_time_preference(day_slots, time_preference)

            if filtered_slots:
                # User's date + time preference has slots
                selected_slots_for_llm = filtered_slots[:8]  # Max 8 slots
                time_period = "morning" if time_preference == "morning" else "afternoon"
                formatted_date = day_slots[0]['formatted_date']
                task_content = f"For {formatted_date} in the {time_period}, here are available time slots for your appointment:"
                logger.info(f"✅ PERFECT MATCH: {len(selected_slots_for_llm)} {time_period} slots on {user_preferred_date}")
            else:
                # No slots for preferred time, offer alternatives
                other_time_slots = filter_slots_by_time_preference(day_slots, "afternoon" if time_preference == "morning" else "morning")
                alternative_time = "afternoon" if time_preference == "morning" else "morning"
                formatted_date = day_slots[0]['formatted_date']

                if other_time_slots:
                    selected_slots_for_llm = other_time_slots[:8]
                    task_content = f"Sorry, no {time_preference} slots available on {formatted_date}. However, we have {alternative_time} appointments available:"
                    logger.info(f"⚠️ FALLBACK: No {time_preference} slots, showing {len(selected_slots_for_llm)} {alternative_time} slots")
                else:
                    # No slots for this date at all in any time, show other dates
                    available_dates = [f"{slots_by_date[date][0]['formatted_date']} ({len(slots_by_date[date])} slots)"
                                     for date in sorted(slots_by_date.keys()) if date != user_preferred_date]
                    dates_text = "\n- ".join(available_dates)
                    task_content = f"Sorry, no appointments available on {formatted_date}. We have appointments on these dates:\n\n- {dates_text}\n\nWhich date would you prefer?"
                    logger.info(f"❌ NO SLOTS: User's preferred date has no slots in any time period")
        else:
            # No time preference, show all slots for the day
            selected_slots_for_llm = day_slots[:8]  # Max 8 slots
            formatted_date = day_slots[0]['formatted_date']
            task_content = f"For {formatted_date}, here are available time slots for your appointment:"
            logger.info(f"✅ WHOLE DAY: {len(selected_slots_for_llm)} slots for {user_preferred_date}")

    else:
        # User's preferred date not available, show available dates
        available_dates = []
        for date_key in sorted(slots_by_date.keys()):
            day_slots = slots_by_date[date_key]
            formatted_date = day_slots[0]['formatted_date']
            slots_count = len(day_slots)
            available_dates.append(f"{formatted_date} ({slots_count} slots available)")

        dates_text = "\n- ".join(available_dates)
        if user_preferred_date:
            task_content = f"Sorry, no appointments available on your preferred date. We have appointments on these dates:\n\n- {dates_text}\n\nWhich date would you prefer? Once you choose a date, I'll show you the available times for that date."
            logger.info(f"❌ DATE UNAVAILABLE: User's preferred date {user_preferred_date} not in available dates")
        else:
            task_content = f"We have appointments available on these dates:\n\n- {dates_text}\n\nWhich date would you prefer? Then I'll show you the available times."
            logger.info(f"ℹ️ DATE SELECTION: Showing {len(slots_by_date)} available dates")

    # Step 3: Create MINIMAL slot data for LLM AND store full slot data globally
    if selected_slots_for_llm:
        # Store the selected slots for UUID lookup later
        global _current_session_slots
        _current_session_slots = {}

        minimal_slots_for_llm = []
        for slot in selected_slots_for_llm:
            time_key = slot['start_time_24h']
            _current_session_slots[time_key] = slot  # Store full slot data by time

            minimal_slots_for_llm.append({
                'time': slot['start_time_24h'],
                'uuid': slot['providing_entity_availability_uuid'],
                'date': slot['date_key']
            })

        slot_context = {
            'available_times': [slot['time'] for slot in minimal_slots_for_llm],
            'service_name': service.name,
            'slot_count': len(minimal_slots_for_llm),
            'time_to_uuid_map': {slot['time']: slot['uuid'] for slot in minimal_slots_for_llm}
        }

        logger.success(f"🚀 OPTIMIZED: Sending only {len(minimal_slots_for_llm)} slots to LLM instead of {len(slots)}")
        logger.info(f"🚀 Times being sent: {[slot['time'] for slot in minimal_slots_for_llm]}")
        logger.info(f"🚀 Time→UUID mapping: {slot_context['time_to_uuid_map']}")
    else:
        # No specific slots selected, just dates
        slot_context = {
            'available_dates': list(slots_by_date.keys()),
            'service_name': service.name,
            'total_slots': len(slots)
        }
        logger.info(f"🚀 DATE SELECTION: Sending date options to LLM")
    
    # NOTE: task_content and slot_context are already set by the smart filtering logic above
    
    return NodeConfig(
        name="slot_selection",
        role_messages=[{
            "role": "system",
            "content": f"""It's currently 2025. Help the patient select from available appointment slots for {service.name}.

🎯 OPTIMIZED SLOT PRESENTATION: Only the most relevant slots have been pre-filtered for you based on user preferences.

{slot_context.get('slot_count', 'Unknown')} carefully selected slots. When presenting times:
- ALWAYS use 24-hour time format (e.g., 13:40, 15:30) - NEVER convert to 12-hour format
- CRITICAL: ONLY present times from this list: {slot_context.get('available_times', [])}
- IMPORTANT: When speaking times aloud, say them in words:
  * Italian: "nove e zero" for 9:00, "nove e quindici" for 9:15, "tredici e quaranta" for 13:40
  * English: "nine o'clock" for 9:00, "nine fifteen" for 9:15, "thirteen forty" for 13:40

- IMPORTANT: When calling function, use digits: 9:00, 9:15, 13:40, etc.
- Never mention prices, UUIDs, or technical details
- Be conversational and human

🚀 AVAILABLE TIMES: {slot_context.get('available_times', [])}

⚡ CRITICAL: TIME→UUID MAPPING for function calls:
{slot_context.get('time_to_uuid_map', {})}

🚨 MANDATORY: When user selects a time, you MUST:
1. Find the time in the mapping above (e.g., if user says "17:15", look for "17:15" in the mapping)
2. Use the corresponding UUID value (NOT the time) as providing_entity_availability_uuid
3. EXAMPLE: If mapping shows {{"17:15": "05ee29df-7257-4beb-9b46-0efb0625d686"}}
   → providing_entity_availability_uuid = "05ee29df-7257-4beb-9b46-0efb0625d686" (NOT "17:15")

{settings.language_config}"""
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
                        "description": "CRITICAL: Must be the UUID value from the time→UUID mapping (e.g., '05ee29df-7257-4beb-9b46-0efb0625d686'), NOT the time itself. Look up the time in the mapping and use the corresponding UUID value."
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
            ),
            FlowsFunctionSchema(
                name="update_date_preference",
                handler=update_date_and_search_slots,
                description="Update the preferred date when user chooses a different date from the available options and immediately search for slots",
                properties={
                    "preferred_date": {
                        "type": "string",
                        "description": "New preferred appointment date in YYYY-MM-DD format (e.g., '2025-11-26'). Must be one of the available dates shown above."
                    },
                    "time_preference": {
                        "type": "string",
                        "description": "Time preference: 'morning' (8:00-12:00), 'afternoon' (12:00-19:00), or 'any' (no preference). Default is to preserve existing time preference.",
                        "default": "preserve_existing"
                    }
                },
                required=["preferred_date"]
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



def create_booking_summary_confirmation_node(selected_services: List[HealthService], selected_slots: List[Dict], selected_center: HealthCenter, total_cost: float, is_cerba_member: bool = False) -> NodeConfig:
    """Create booking summary confirmation node with all details before personal info collection"""

    # Use full center name directly

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
{selected_center.name}

**Total Cost:** {int(total_cost)} euro{membership_text}

Would you like to proceed with this booking? If yes, I'll just need to collect some personal information to complete your appointment. If you'd like to change the time slot, I can show you other available times for the same service and date."""

    return NodeConfig(
        name="booking_summary_confirmation",
        role_messages=[{
            "role": "system",
            "content": f"CRITICAL: You must present EXACTLY the booking summary provided below. DO NOT change, modify, or hallucinate any times, dates, services, or prices. Use ONLY the exact information from the summary content. DO NOT mention any times other than what is explicitly written in the summary. This is just a summary - the actual booking will be created after collecting personal details. Ask for confirmation before proceeding to personal information collection. If the patient wants to change the time, use action='change' to show other available times for the same service and date. {settings.language_config}"
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
                        "description": "proceed: continue with current booking, cancel: stop completely, change: modify the time slot (keeps same service and date but shows other available times)"
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
