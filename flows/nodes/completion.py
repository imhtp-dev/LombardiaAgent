"""
Success, error, and completion handling nodes
"""

from datetime import datetime
from typing import List, Dict
from pipecat_flows import NodeConfig, FlowsFunctionSchema

from models.requests import HealthService, HealthCenter
from flows.handlers.service_handlers import search_health_services_and_transition
from flows.handlers.booking_handlers import handle_booking_modification


def create_error_node(error_message: str) -> NodeConfig:
    """Dynamically create error node with custom message"""
    return NodeConfig(
        name="booking_error",
        role_messages=[{
            "role": "system",
            "content": "Gestisci l'errore con rammarico e offri alternative utili. Sii empatico e fornisci passaggi chiari."
        }],
        task_messages=[{
            "role": "system",
            "content": f"{error_message} Mi scuso sinceramente per questo inconveniente. Vorresti provare a prenotare di nuovo o cercare un servizio diverso?"
        }],
        functions=[
            FlowsFunctionSchema(
                name="search_health_services",
                handler=search_health_services_and_transition,
                description="Riavvia il processo di prenotazione",
                properties={
                    "search_term": {
                        "type": "string",
                        "description": "Nome del servizio da cercare per riavviare la prenotazione"
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
        
        booking_text = f"Hai prenotato {slot['service_name']} per il {formatted_date} dalle {start_time} alle {end_time} e questo appuntamento costa {int(slot['price'])} euro"
        bookings_text.append(booking_text)
    
    bookings_summary = "\n\n".join(bookings_text)
    
    task_content = f"""Ottime notizie! I tuoi appuntamenti sono confermati.

{bookings_summary}

Il costo totale dei tuoi appuntamenti è {int(total_price)} euro.

Le tue prenotazioni sono confermate e riceverai i dettagli di conferma a breve. Puoi dire cancella prenotazione per cancellare, cambia orario per riprogrammare, o inizia una nuova prenotazione."""
    
    return NodeConfig(
        name="booking_success_multi",
        role_messages=[{
            "role": "system",
            "content": "Siamo attualmente nel 2025. Celebra le prenotazioni riuscite in modo caloroso e umano. Di' sempre 'euro' invece di usare il simbolo €. Parla naturalmente come un assistente amichevole."
        }],
        task_messages=[{
            "role": "system",
            "content": task_content
        }],
        functions=[
            FlowsFunctionSchema(
                name="manage_booking",
                handler=handle_booking_modification,
                description="Cancella o modifica prenotazioni esistenti",
                properties={
                    "action": {
                        "type": "string",
                        "description": "Azione da intraprendere: 'cancel' per cancellare la prenotazione, 'change_time' per riprogrammare"
                    }
                },
                required=["action"]
            ),
            FlowsFunctionSchema(
                name="start_new_booking",
                handler=search_health_services_and_transition,
                description="Inizia un nuovo processo di prenotazione",
                properties={
                    "search_term": {
                        "type": "string",
                        "description": "Nome del servizio da cercare per una nuova prenotazione"
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
            "content": "Gestisci la cancellazione della prenotazione e offri di riavviare."
        }],
        task_messages=[{
            "role": "system",
            "content": "Nessun problema! La tua prenotazione è stata cancellata. Vorresti iniziare una nuova prenotazione per un servizio diverso o riprovare?"
        }],
        functions=[
            FlowsFunctionSchema(
                name="search_health_services",
                handler=search_health_services_and_transition,
                description="Inizia un nuovo processo di prenotazione",
                properties={
                    "search_term": {
                        "type": "string",
                        "description": "Nome del servizio da cercare"
                    }
                },
                required=["search_term"]
            )
        ]
    )