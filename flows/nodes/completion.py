"""
Success, error, and completion handling nodes
"""

from datetime import datetime
from typing import List, Dict
from pipecat_flows import NodeConfig, FlowsFunctionSchema

from models.requests import HealthService, HealthCenter
from flows.handlers.service_handlers import search_health_services_and_transition
from flows.handlers.booking_handlers import handle_booking_modification
from config.settings import settings


def create_error_node(error_message: str) -> NodeConfig:
    """Dynamically create error node with custom message"""
    return NodeConfig(
        name="booking_error",
        role_messages=[{
            "role": "system",
            "content": f"Handle the error with regret and offer helpful alternatives. Be empathetic and provide clear steps. {settings.language_config}"
        }],
        task_messages=[{
            "role": "system",
            "content": f"{error_message} I sincerely apologize for this inconvenience. Would you like to try booking again or search for a different service?"
        }],
        functions=[
            FlowsFunctionSchema(
                name="search_health_services",
                handler=search_health_services_and_transition,
                description="Restart the booking process",
                properties={
                    "search_term": {
                        "type": "string",
                        "description": "Name of the service to search for to restart booking"
                    }
                },
                required=["search_term"]
            )
        ]
    )


def create_booking_success_multi_node(booked_slots: List[Dict], total_price: float) -> NodeConfig:
    """Create booking success node with all booking details"""
    bookings_text = []
    for slot in booked_slots:
        # Convert time format to human readable
        start_time_str = slot['start_time'].replace("T", " ").replace("+00:00", "")
        end_time_str = slot['end_time'].replace("T", " ").replace("+00:00", "")
        
        # Format datetime to human readable
        start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
        
        formatted_date = start_dt.strftime("%d %B")
        start_time = start_dt.strftime("%-H:%M")
        end_time = end_dt.strftime("%-H:%M")
        
        booking_text = f"You have booked {slot['service_name']} for {formatted_date} from {start_time} to {end_time} and this appointment costs {int(slot['price'])} euros"
        bookings_text.append(booking_text)
    
    bookings_summary = "\n\n".join(bookings_text)
    
    task_content = f"""Great news! Your appointments are confirmed.

{bookings_summary}

The total cost of your appointments is {int(total_price)} euros.

Your bookings are confirmed and you will receive confirmation details shortly. You can say cancel booking to cancel, change time to reschedule, or start a new booking."""
    
    return NodeConfig(
        name="booking_success_multi",
        role_messages=[{
            "role": "system",
            "content": f"We are currently in 2025. Celebrate successful bookings in a warm and human way. Always say 'euros' instead of using the € symbol. Speak naturally like a friendly assistant. {settings.language_config}"
        }],
        task_messages=[{
            "role": "system",
            "content": task_content
        }],
        functions=[
            FlowsFunctionSchema(
                name="manage_booking",
                handler=handle_booking_modification,
                description="Cancel or modify existing bookings",
                properties={
                    "action": {
                        "type": "string",
                        "description": "Action to take: 'cancel' to cancel the booking, 'change_time' to reschedule"
                    }
                },
                required=["action"]
            ),
            FlowsFunctionSchema(
                name="start_new_booking",
                handler=search_health_services_and_transition,
                description="Start a new booking process",
                properties={
                    "search_term": {
                        "type": "string",
                        "description": "Name of the service to search for a new booking"
                    }
                },
                required=["search_term"]
            )
        ]
    )


def create_restart_node() -> NodeConfig:
    """Create restart node for cancelled bookings"""
    return NodeConfig(
        name="restart_booking",
        role_messages=[{
            "role": "system",
            "content": f"Handle booking cancellation and offer to restart. {settings.language_config}"
        }],
        task_messages=[{
            "role": "system",
            "content": "No problem! Your booking has been cancelled. Would you like to start a new booking for a different service or try again?"
        }],
        functions=[
            FlowsFunctionSchema(
                name="search_health_services",
                handler=search_health_services_and_transition,
                description="Start a new booking process",
                properties={
                    "search_term": {
                        "type": "string",
                        "description": "Name of the service to search for"
                    }
                },
                required=["search_term"]
            )
        ]
    )