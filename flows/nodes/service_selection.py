"""
Service search and selection nodes
"""

from typing import List
from pipecat_flows import NodeConfig, FlowsFunctionSchema

from models.requests import HealthService
from flows.handlers.service_handlers import (
    select_service_and_transition, 
    refine_search_and_transition,
    search_health_services_and_transition
)


def create_service_selection_node(services: List[HealthService] = None, search_term: str = "") -> NodeConfig:
    """Dynamically create enhanced service selection node with top 3 services"""
    if services:
        # Format services for presentation (top 3)
        top_services = services[:3]
        service_options = "\n".join([service.name for service in top_services])
        
        task_content = f"""Ho trovato questi servizi per '{search_term}':

{service_options}

Scegli uno di questi servizi, o dimmi 'pronuncia il nome completo del servizio' se nessuno di questi corrisponde a quello che stai cercando."""
    else:
        task_content = "Scegli uno dei servizi trovati, o dimmi 'pronuncia il nome completo del servizio' per una ricerca più specifica."
    
    return NodeConfig(
        name="service_selection",
        role_messages=[{
            "role": "system",
            "content": "Aiuta il paziente a scegliere tra i primi 3 risultati di ricerca, e digli anche che se nessuno di questi servizi corrisponde, dovrebbe dire il nome completo del servizio per affinare la ricerca. **CRITICO: NON usare MAI 1., 2., 3., o numeri quando elenchi i servizi. Elenca solo i nomi dei servizi separati da virgole o interruzioni di riga, senza prefissi numerici.** Parla naturalmente come un essere umano."
        }],
        task_messages=[{
            "role": "system",
            "content": task_content
        }],
        functions=[
            FlowsFunctionSchema(
                name="select_service",
                handler=select_service_and_transition,
                description="Seleziona un servizio specifico dai risultati di ricerca",
                properties={
                    "service_uuid": {
                        "type": "string",
                        "description": "UUID del servizio sanitario selezionato"
                    }
                },
                required=["service_uuid"]
            ),
            FlowsFunctionSchema(
                name="refine_search",
                handler=refine_search_and_transition,
                description="Affina la tua ricerca con un nome di servizio più specifico",
                properties={
                    "refined_search_term": {
                        "type": "string",
                        "description": "Nome del servizio più specifico per la ricerca affinata"
                    }
                },
                required=["refined_search_term"]
            )
        ]
    )


def create_search_retry_node(error_message: str) -> NodeConfig:
    """Dynamically create node for search retry with custom error message"""
    return NodeConfig(
        name="search_retry",
        role_messages=[{
            "role": "system",
            "content": "Aiuta il paziente a provare di nuovo la ricerca del servizio con un termine migliore."
        }],
        task_messages=[{
            "role": "system",
            "content": f"{error_message} Prova a cercare con il nome completo del servizio.'"
        }],
        functions=[
            FlowsFunctionSchema(
                name="search_health_services",
                handler=search_health_services_and_transition,
                description="Cerca servizi sanitari utilizzando la ricerca fuzzy",
                properties={
                    "search_term": {
                        "type": "string",
                        "description": "Nome del servizio da cercare (ad es. 'cardiologia', 'analisi del sangue', 'radiografia alla caviglia')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Numero massimo di risultati da restituire (predefinito: 3, massimo: 5)",
                        "default": 3,
                        "minimum": 1,
                        "maximum": 5
                    }
                },
                required=["search_term"]
            )
        ]
    )