"""
Final booking completion nodes
"""

from datetime import datetime
from typing import List, Dict
from pipecat_flows import NodeConfig, FlowsFunctionSchema

from flows.handlers.service_handlers import search_health_services_and_transition


def create_booking_success_final_node(booking_info: Dict, selected_services: List, booked_slots: List[Dict]) -> NodeConfig:
    """Create final booking success node with complete booking details"""

    # Format booking details
    services_text = ", ".join([service.name for service in selected_services])
    booking_code = booking_info.get("code", "N/A")
    booking_uuid = booking_info.get("uuid", "N/A")
    creation_date = booking_info.get("created_at", "")

    # Format slot details
    slots_details = []
    total_price = 0

    for i, slot in enumerate(booked_slots):
        # Convert time format to human readable
        start_time_str = slot['start_time'].replace("T", " ").replace("+00:00", "")
        end_time_str = slot['end_time'].replace("T", " ").replace("+00:00", "")

        start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")

        formatted_date = start_dt.strftime("%d %B %Y")
        start_time = start_dt.strftime("%-H:%M")
        end_time = end_dt.strftime("%-H:%M")

        service_name = selected_services[i].name if i < len(selected_services) else "Service"
        price = slot.get('price', 0)
        total_price += price

        slots_details.append(f"• {service_name} il {formatted_date} dalle {start_time} alle {end_time} - {int(price)} euro")

    # Create confirmation message
    if creation_date:
        try:
            created_dt = datetime.fromisoformat(creation_date.replace('Z', '+00:00'))
            created_date = created_dt.strftime("%d %B %Y at %-H:%M")
        except:
            created_date = creation_date
    else:
        created_date = datetime.now().strftime("%d %B %Y at %-H:%M")

    task_content = f"""🎉 Eccellente! La tua prenotazione è stata creata con successo!

**Dettagli Prenotazione:**
• Codice Prenotazione: **{booking_code}**
• ID Prenotazione: {booking_uuid}
• Creata: {created_date}

**I Tuoi Appuntamenti:**
{chr(10).join(slots_details)}

**Costo Totale: {int(total_price)} euro**

Riceverai un'email di conferma con tutti i dettagli. Grazie per aver scelto Cerba Healthcare!

C'è qualcos'altro con cui posso aiutarti oggi?"""

    return NodeConfig(
        name="booking_success_final",
        role_messages=[{
            "role": "system",
            "content": "Celebra il completamento della prenotazione con calore e professionalità. Di' sempre 'euro' invece di usare il simbolo €. Parla naturalmente come un assistente amichevole."
        }],
        task_messages=[{
            "role": "system",
            "content": task_content
        }],
        functions=[
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