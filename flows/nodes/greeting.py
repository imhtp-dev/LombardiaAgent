"""
Greeting and initial conversation nodes
"""

from pipecat_flows import NodeConfig, FlowsFunctionSchema
from flows.handlers.service_handlers import search_health_services_and_transition


def create_greeting_node() -> NodeConfig:
    """Create the initial greeting node"""
    return NodeConfig(
        name="greeting",
        role_messages=[{
            "role": "system",
            "content": "Sei Ualà, un assistente virtuale calma e amichevole (voce femminile) per Cerba Healthcare. Parla con calore e chiarezza come un essere umano, non come un robot."
        }],
        task_messages=[{
            "role": "system",
            "content": "Dì: 'Ciao, sono Ualà, un assistente virtuale per Cerba Healthcare. Puoi dirmi quale servizio vorresti prenotare?' Quando l'utente menziona QUALSIASI nome di servizio, chiama immediatamente search_health_services per cercarlo."
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