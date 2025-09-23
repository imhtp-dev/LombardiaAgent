"""
Patient information collection nodes
"""

from pipecat_flows import NodeConfig, FlowsFunctionSchema
from flows.handlers.patient_handlers import (
    collect_address_and_transition,
    collect_gender_and_transition,
    collect_dob_and_transition,
    verify_basic_info_and_transition
)


def create_collect_address_node() -> NodeConfig:
    """Create address collection node"""
    return NodeConfig(
        name="collect_address",
        role_messages=[{
            "role": "system",
            "content": "Raccogli l'indirizzo del paziente per trovare centri sanitari nelle vicinanze."
        }],
        task_messages=[{
            "role": "system",
            "content": "Perfetto! Ora ho bisogno del tuo indirizzo o città per trovare centri sanitari nelle vicinanze. Per favore dimmi il tuo indirizzo."
        }],
        functions=[
            FlowsFunctionSchema(
                name="collect_address",
                handler=collect_address_and_transition,
                description="Raccogli l'indirizzo del paziente",
                properties={
                    "address": {
                        "type": "string",
                        "description": "Indirizzo o città del paziente"
                    }
                },
                required=["address"]
            )
        ]
    )


def create_collect_gender_node() -> NodeConfig:
    """Create gender collection node"""
    return NodeConfig(
        name="collect_gender",
        role_messages=[{
            "role": "system",
            "content": "Chiedi al paziente il suo genere e aspetta la sua risposta prima di chiamare qualsiasi funzione."
        }],
        task_messages=[{
            "role": "system",
            "content": "Per favore dimmi il tuo genere. Sei maschio o femmina?"
        }],
        functions=[
            FlowsFunctionSchema(
                name="collect_gender",
                handler=collect_gender_and_transition,
                description="Raccogli il genere del paziente",
                properties={
                    "gender": {
                        "type": "string",
                        "description": "Genere del paziente (maschio/femmina)"
                    }
                },
                required=["gender"]
            )
        ]
    )


def create_collect_dob_node() -> NodeConfig:
    """Create DOB collection node"""
    return NodeConfig(
        name="collect_dob",
        role_messages=[{
            "role": "system",
            "content": "Raccogli la data di nascita del paziente per la prenotazione. Sii flessibile con i formati delle date e converti internamente qualsiasi data in linguaggio naturale nel formato YYY-MM-DD. Non comunicare mai all'utente i requisiti di formato. Chiedi semplicemente e lascia che sia l'LLM a occuparsi della conversione."
        }],
        task_messages=[{
            "role": "system",
            "content": "Potresti darmi la tua data di nascita?"
        }],
        functions=[
            FlowsFunctionSchema(
                name="collect_dob",
                handler=collect_dob_and_transition,
                description="Raccogli la data di nascita del paziente",
                properties={
                    "date_of_birth": {
                        "type": "string",
                        "description": "Date of birth in YYYY-MM-DD format"
                    }
                },
                required=["date_of_birth"]
            )
        ]
    )


def create_verify_basic_info_node(address: str, gender: str, dob: str) -> NodeConfig:
    """Create verification node for address, gender, and DOB"""
    gender_display = "Male" if gender.lower() == "m" else "Female" if gender.lower() == "f" else gender

    verification_text = f"""Verifica le informazioni che ho raccolto:

Indirizzo: {address}
Sesso: {gender_display}
Data di nascita: {dob}

Questi dati sono corretti? Rispondi "sì" se sono corretti, oppure indicami cosa deve essere modificato."""

    return NodeConfig(
        name="verify_basic_info",
        role_messages=[{
            "role": "system",
            "content": "Presentare le informazioni del paziente per la verifica. Se l'utente risponde 'sì', confermare tutti i dettagli. Se l'utente desidera modificare qualcosa di specifico (ad esempio 'cambiare sesso in maschile'), aggiornare solo quel campo. Ascoltare cosa desidera modificare ed estrarre il nome del campo e il nuovo valore."
        }],
        task_messages=[{
            "role": "system",
            "content": verification_text
        }],
        functions=[
            FlowsFunctionSchema(
                name="verify_basic_info",
                handler=verify_basic_info_and_transition,
                description="Handle verification response - confirm all details or update specific field",
                properties={
                    "action": {
                        "type": "string",
                        "enum": ["confirm", "change"],
                        "description": "confirm if user says yes, change if user wants to modify something"
                    },
                    "field_to_change": {
                        "type": "string",
                        "enum": ["address", "gender", "date_of_birth"],
                        "description": "Which field to change (only if action is 'change')"
                    },
                    "new_value": {
                        "type": "string",
                        "description": "New value for the field (only if action is 'change')"
                    }
                },
                required=["action"]
            )
        ]
    )