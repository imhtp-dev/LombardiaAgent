"""
Booking and appointment management nodes
"""

import json
from datetime import datetime, timedelta
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
    handle_booking_modification
)


def create_orange_box_node() -> NodeConfig:
    """Create the Orange Box node that generates decision flows"""
    return NodeConfig(
        name="orange_box_flow_generation", 
        role_messages=[{
            "role": "system",
            "content": "Genera il flusso decisionale basato sulle caratteristiche del servizio sanitario selezionato."
        }],
        task_messages=[{
            "role": "system",
            "content": "Ora analizzerò il servizio selezionato per determinare se ci sono requisiti speciali o opzioni aggiuntive. Aspetta un momento per favore."
        }],
        functions=[
            FlowsFunctionSchema(
                name="generate_flow",
                handler=generate_flow_and_transition,
                description="Genera il flusso decisionale per il servizio selezionato",
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
            "content": f"""Stai navigando in un flusso decisionale per il servizio sanitario: {service_name}
            
SEGUI QUESTA ESATTA STRUTTURA DI FLUSSO: {json.dumps(generated_flow, indent=2)}
            
ISTRUZIONI IMPORTANTI:
1. Iniziare con il messaggio principale del flusso
2. Presentare le domande esattamente come scritto nel flusso
3. Seguire i rami sì/no in base alle risposte dell'utente
4. Quando si presentano le opzioni di servizio, mostrare SOLO i nomi dei servizi da list_health_services - NON menzionare MAI gli UUID
5. Se list_health_services è vuoto in una domanda ma contiene servizi nei rami di risposta, mostrare tali servizi quando si pone la domanda
6. Quando l'utente seleziona servizi aggiuntivi, monitorarli internamente con i loro UUID
7. Quando l'utente risponde "sì" alle domande sulla visita specialistica, includere tali servizi specialistici
8. Quando si raggiunge un'azione finale (save_cart, ecc.), chiamare la funzione finalize_services
9. CRITICO: includere TUTTI i servizi scelti dall'utente durante la conversazione

**REGOLE CRITICHE:**
- NON menzionare MAI gli UUID agli utenti - sono solo interni
- NON utilizzare MAI 1, 2, 3 o numeri quando si presentano i servizi
- Elencare solo i nomi dei servizi separati da virgole o A capo, senza prefissi numerici
- Se una domanda riguarda i servizi ma list_health_services è vuoto, controlla i rami delle risposte per i servizi disponibili da visualizzare

Logica decisionale del flusso:
- Se l'utente sceglie servizi aggiuntivi dall'elenco principale, includi tali servizi
- Se l'utente risponde SÌ alle domande relative alle visite specialistiche, includi i servizi specialistici da quel ramo
- Se l'utente risponde NO, segui il ramo "no" di conseguenza

FONDAMENTALE: Quando si pongono domande sui servizi:
- Se la domanda corrente ha list_health_services con elementi, mostra tali servizi
- Se la domanda corrente ha list_health_services vuoto ma i rami "sì" o "no" contengono list_health_services, mostra QUEI servizi nella tua domanda
- Esempio: la domanda chiede "Desidera una consulenza specialistica?" e il ramo "sì" ha list_health_services: ["Visita Cardiologica"], quindi di' "Desideri prenotare una visita specialistica? La visita specialistica disponibile è: Visita Cardiologica"
- Mostra sempre solo i nomi dei servizi, mai UUID, mai numeri

Sii colloquiale ma segui attentamente la struttura del flusso. Parla sempre come un essere umano, non come un robot."""
        }],
        task_messages=[{
            "role": "system",
            "content": f"Avviare il flusso decisionale per {service_name}. Iniziare con il messaggio principale dal flusso generato."
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
            "content": "Cerca centri sanitari che forniscono tutti i servizi selezionati."
        }],
        task_messages=[{
            "role": "system",
            "content": "Perfetto! Ora cercherò centri sanitari che possono fornire tutti i servizi selezionati. Aspetta un momento per favore."
        }],
        functions=[
            FlowsFunctionSchema(
                name="search_final_centers",
                handler=search_final_centers_and_transition,
                description="Cerca centri sanitari con tutti i servizi selezionati",
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
    
    task_content = f"""Perfetto! Ho trovato questi centri sanitari che possono fornire i tuoi servizi ({service_names}):

{center_options}

Quale centro sanitario preferiresti per il tuo appuntamento? Dimmi solo il nome o il numero."""
    
    return NodeConfig(
        name="final_center_selection",
        role_messages=[{
            "role": "system",
            "content": f"""Siamo attualmente nel 2025. Stai aiutando un paziente a scegliere tra {len(top_centers)} centri sanitari che possono fornire i loro servizi: {service_names}.

IMPORTANTE: Devi presentare chiaramente i centri sanitari e chiedere al paziente di sceglierne uno. Non dire mai frasi generiche come "completa la prenotazione" - invece, presenta i centri specifici e chiedi di scegliere.

Quando il paziente seleziona un centro, chiama la funzione select_center con l'UUID corretto del centro.

Centri disponibili:
{chr(10).join([f"- {center.name} (UUID: {center.uuid})" for center in top_centers])}

Parla sempre naturalmente come un essere umano e di' 'euro' invece del simbolo €."""
        }],
        task_messages=[{
            "role": "system",
            "content": task_content
        }],
        functions=[
            FlowsFunctionSchema(
                name="select_center",
                handler=select_center_and_book,
                description="Seleziona un centro sanitario per la prenotazione",
                properties={
                    "center_uuid": {
                        "type": "string",
                        "description": "UUID del centro sanitario selezionato"
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
            "content": f"Nessun centro sanitario trovato in {address} per {service_name}. Scusati e chiedi se desiderano provare una sede o un servizio diverso. Offriti di ricominciare da capo."
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
            "content": "Chiedere al paziente se è un membro Cerba per calcolare i prezzi."
        }],
        task_messages=[{
            "role": "system",
            "content": "Hai una Cerba Card?"
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
            "content": "L'anno corrente è il 2025. Raccogli la data preferita e l'orario opzionale per l'appuntamento. Se l'utente dice 'mattina' o menziona l'orario mattutino, preferisce le 08:00-12:00 (formato 24 ore). Se dice 'pomeriggio' o menziona l'orario pomeridiano, preferisce le 12:00-19:00 (formato 24 ore). Utilizza e visualizza sempre il formato 24 ore (ad esempio 13:40, 15:30) - NON convertire MAI nel formato 12 ore. Converti internamente la data in linguaggio naturale dell'utente nel formato YYY-MM-DD. Sii flessibile con i formati di input dell'utente. Parla in modo naturale come un essere umano."
        }],
        task_messages=[{
            "role": "system",
            "content": "Quale data e ora preferisci per il tuo appuntamento? "
        }],
        functions=[
            FlowsFunctionSchema(
                name="collect_datetime",
                handler=collect_datetime_and_transition,
                description="Collect preferred appointment date and optional time preference",
                properties={
                    "preferred_date": {
                        "type": "string",
                        "description": "Data preferita per l'appuntamento nel formato YYYY-MM-DD"
                    },
                    "preferred_time": {
                        "type": "string",
                        "description": "Orario preferito per l'appuntamento (orario specifico come '09:00', '14:30' o intervallo di tempo come 'mattina', 'pomeriggio')"
                    },
                    "time_preference": {
                        "type": "string",
                        "description": "Preferenza oraria: 'mattina' (8:00-12:00), 'pomeriggio' (12:00-19:00), 'specifico' (orario esatto) o 'qualsiasi' (nessuna preferenza)"
                    }
                },
                required=["preferred_date"]
            )
        ]
    )


def create_collect_datetime_node_for_service(service_name: str = None, is_multi_service: bool = False) -> NodeConfig:
    """Create date and time collection node, optionally for specific service"""
    if is_multi_service and service_name:
        task_content = f"Che data e orario preferiresti per il tuo appuntamento di {service_name}?"
        node_name = f"collect_datetime_{service_name.lower().replace(' ', '_')}"
    else:
        task_content = "Che data e orario preferiresti per il tuo appuntamento?"
        node_name = "collect_datetime"
    
    return NodeConfig(
        name=node_name,
        role_messages=[{
            "role": "system",
            "content": "Raccogli la data e l'ora preferite per l'appuntamento. Converti internamente la data/ora in linguaggio naturale dell'utente nel formato AAAA-MM-GG e nel formato 24 ore. Sii flessibile con i formati di input dell'utente."
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
                        "description": "Data preferita per l'appuntamento nel formato YYYY-MM-DD"
                    },
                    "preferred_time": {
                        "type": "string",
                        "description": "Orario preferito per l'appuntamento (ad es., '09:00', '14:30')"
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
            "content": "Cerca slot di appuntamento disponibili per il servizio e l'orario selezionati."
        }],
        task_messages=[{
            "role": "system",
            "content": "Lascia che cerchi slot di appuntamento disponibili per la tua data e orario preferiti. Aspetta un momento per favore..."
        }],
        functions=[
            FlowsFunctionSchema(
                name="search_slots",
                handler=search_slots_and_transition,
                description="Cerca slot di appuntamento disponibili",
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
    
    for slot in slots:
        # Parse slot data
        start_time_str = slot["start_time"].replace("T", " ").replace("+00:00", "")
        end_time_str = slot["end_time"].replace("T", " ").replace("+00:00", "")
        
        start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
        end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
        
        date_key = start_dt.strftime("%Y-%m-%d")
        formatted_date = start_dt.strftime("%d %B")
        
        # Format times in 24-hour format without leading zeros
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
            task_content = f"Ottimo! Abbiamo uno slot disponibile per {service.name} il {formatted_date} dalle {slot['start_time_24h']} alle {slot['end_time_24h']}. Vorresti che prenotassi questo appuntamento per te alle {slot['start_time_24h']}?"
        elif len(day_slots) <= 6:
            # Few slots - show them in a natural way
            if afternoon_slots and not morning_slots:
                # Only afternoon slots
                first_slot = afternoon_slots[0]
                last_slot = afternoon_slots[-1] if len(afternoon_slots) > 1 else first_slot
                task_content = f"Abbiamo appuntamenti disponibili per {service.name} nel pomeriggio il {formatted_date} dalle {first_slot['start_time_24h']} alle {last_slot['end_time_24h']}. Quale orario andrebbe meglio per te? Posso prenotarti alle {first_slot['start_time_24h']} o qualsiasi altro orario disponibile."
            elif morning_slots and not afternoon_slots:
                # Only morning slots
                first_slot = morning_slots[0]
                last_slot = morning_slots[-1] if len(morning_slots) > 1 else first_slot
                task_content = f"Abbiamo appuntamenti disponibili per {service.name} la mattina il {formatted_date} dalle {first_slot['start_time_24h']} alle {last_slot['end_time_24h']}. Quale orario andrebbe meglio per te? Posso prenotarti alle {first_slot['start_time_24h']} o qualsiasi altro orario disponibile."
            else:
                # Both morning and afternoon
                morning_first = morning_slots[0]['start_time_24h'] if morning_slots else None
                afternoon_first = afternoon_slots[0]['start_time_24h'] if afternoon_slots else None
                if morning_first and afternoon_first:
                    task_content = f"Abbiamo appuntamenti disponibili per {service.name} il {formatted_date}. Posso prenotarti la mattina a partire dalle {morning_first} o il pomeriggio a partire dalle {afternoon_first}. Quale preferenza oraria andrebbe meglio per te?"
                else:
                    first_slot = day_slots[0]
                    task_content = f"Abbiamo appuntamenti disponibili per {service.name} il {formatted_date}. L'orario più presto disponibile è alle {first_slot['start_time_24h']}. Dovrei prenotare questo orario per te o preferiresti un orario diverso?"
        else:
            # Many slots - group and be natural
            availability_text = f"Abbiamo diversi appuntamenti disponibili per {service.name} il {formatted_date}:\n\n"
            
            if morning_slots:
                morning_times = [f"{s['start_time_24h']} to {s['end_time_24h']}" for s in morning_slots[:3]]
                availability_text += f"Orari mattutini: {', '.join(morning_times)}\n"
            
            if afternoon_slots:
                afternoon_times = [f"{s['start_time_24h']} to {s['end_time_24h']}" for s in afternoon_slots[:3]]
                availability_text += f"Orari pomeridiani: {', '.join(afternoon_times)}\n"
            
            task_content = f"{availability_text}\nQuale orario funziona meglio per te? Dimmi semplicemente il tuo orario preferito e lo prenoterò per te."
        
    else:
        # Multiple days - show available dates and suggest choosing one
        available_dates = []
        for date_key in sorted(slots_by_date.keys())[:3]:  # Show max 3 dates
            day_slots = slots_by_date[date_key]
            formatted_date = day_slots[0]['formatted_date']
            slots_count = len(day_slots)
            available_dates.append(f"{formatted_date} ({slots_count} slots available)")
        
        dates_text = "\n- ".join(available_dates)
        task_content = f"Abbiamo appuntamenti disponibili in queste date:\n\n- {dates_text}\n\nQuale data preferiresti? Poi ti mostrerò gli orari disponibili per quel giorno."
    
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
            "content": f"""Al momento è il 2025. Aiuta il paziente a selezionare tra gli slot di appuntamento disponibili per {service.name}.

Hai {len(slot)} slot disponibili. Quando presenti gli slot:
- Usa SEMPRE il formato orario a 24 ore (ad esempio, 13:40, 15:30) - NON convertire MAI nel formato a 12 ore
- Non menzionare mai prezzi, UUID o dettagli tecnici
- Sii colloquiale e umano
- Parla in modo naturale, come se stessi suggerendo un orario specifico: "Devo prenotarti alle 13:40?"
- Di' sempre "euro" a parole, non il simbolo €

Dati sugli slot disponibili: {slot_context}"""
        }],
        task_messages=[{
            "role": "system",
            "content": task_content
        }],
        functions=[
            FlowsFunctionSchema(
                name="select_slot",
                handler=select_slot_and_book,
                description="Seleziona uno slot di appuntamento specifico fornendo l'UUID dello slot",
                properties={
                    "providing_entity_availability_uuid": {
                        "type": "string",
                        "description": "UUID della disponibilità dell'entità fornitrice dello slot selezionato"
                    },
                    "selected_time": {
                        "type": "string",
                        "description": "Orario leggibile dello slot selezionato (ad es., '09:30 - 10:00')"
                    },
                    "selected_date": {
                        "type": "string",
                        "description": "Data leggibile dello slot selezionato (ad es., '21 novembre 2025')"
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
            "content": "Conferma i dettagli della prenotazione e crea l'appuntamento."
        }],
        task_messages=[{
            "role": "system",
            "content": "Perfetto! Sono pronto a prenotare il tuo appuntamento. Per favore conferma se vuoi procedere con questa prenotazione."
        }],
        functions=[
            FlowsFunctionSchema(
                name="create_booking",
                handler=create_booking_and_transition,
                description="Crea la prenotazione dell'appuntamento",
                properties={
                    "confirm_booking": {
                        "type": "boolean",
                        "description": "Conferma per procedere con la prenotazione (vero/falso)"
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
            "content": f"Lo slot selezionato per {service_name} non è più disponibile. Cerca nuovi slot disponibili e presentali al paziente. Sii apologetico e utile."
        }],
        task_messages=[{
            "role": "system",
            "content": f"Mi scuso, ma quello slot orario per {service_name} è stato appena prenotato da qualcun altro. Lascia che cerchi altri orari disponibili per te."
        }],
        functions=[
            FlowsFunctionSchema(
                name="search_slots",
                handler=search_slots_and_transition,
                description="Cerca slot disponibili aggiornati",
                properties={},
                required=[]
            )
        ],
        respond_immediately=True  # Automatically trigger slot search
    )


def create_no_slots_node(date: str, time_preference: str = "any time") -> NodeConfig:
    """Create node when no slots are available - with human-like alternative suggestions"""
    if time_preference == "any time":
        no_slots_message = f"Mi dispiace, non ci sono posti disponibili per il giorno {date}. Vorrei suggerirti delle alternative: vorresti provare una data diversa? Posso anche verificare se ci sono posti disponibili in date vicine, ad esempio qualche giorno prima o qualche giorno dopo."
    else:
        no_slots_message = f"Mi dispiace, non ci sono posti disponibili per il giorno {date} per il giorno {time_preference}. Vorrei suggerirti alcune alternative: vorresti provare una data o un orario diverso? Ad esempio, potremmo avere posti disponibili per il giorno {date} a un orario diverso o in un'altra data."
    
    return NodeConfig(
        name="no_slots_available",
        role_messages=[{
            "role": "system",
            "content": "Siamo nel 2025. Quando non ci sono slot disponibili, sii disponibile e suggerisci alternative in modo umano. Offriti di cercare date o orari diversi. Non menzionare mai dettagli tecnici o UUID. Dì sempre 'euro' invece del simbolo €."
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
                        "description": "Nuova data di appuntamento preferita nel formato YYYY-MM-DD "
                    },
                    "preferred_time": {
                        "type": "string",
                        "description": "Nuovo orario preferito per l'appuntamento (orario specifico come '09:00', '14:30' o intervallo di tempo come 'mattina', 'pomeriggio')"
                    },
                    "time_preference": {
                        "type": "string",
                        "description": "Preferenza oraria: 'mattina' (8:00-12:00), 'pomeriggio' (12:00-19:00), 'specifico' (orario esatto) o 'qualsiasi' (nessuna preferenza)"
                    }
                },
                required=["preferred_date"]
            )
        ]
    )