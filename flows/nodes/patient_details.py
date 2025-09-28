"""
Patient details collection nodes for booking finalization
"""

from pipecat_flows import NodeConfig, FlowsFunctionSchema
from flows.handlers.patient_detail_handlers import (
    collect_name_and_transition,
    collect_surname_and_transition,
    collect_phone_and_transition,
    collect_email_and_transition,
    confirm_email_and_transition,
    collect_reminder_authorization_and_transition,
    collect_marketing_authorization_and_transition,
    confirm_details_and_create_booking
)


def create_collect_name_node() -> NodeConfig:
    """Create name collection node"""
    return NodeConfig(
        name="collect_name",
        role_messages=[{
            "role": "system",
            "content": "Raccogli il nome del paziente per finalizzare la prenotazione."
        }],
        task_messages=[{
            "role": "system",
            "content": "Qual è il tuo nome?"
        }],
        functions=[
            FlowsFunctionSchema(
                name="collect_name",
                handler=collect_name_and_transition,
                description="Raccogli il nome del paziente",
                properties={
                    "name": {
                        "type": "string",
                        "description": "Nome del paziente"
                    }
                },
                required=["name"]
            )
        ]
    )


def create_collect_surname_node() -> NodeConfig:
    """Create surname collection node"""
    return NodeConfig(
        name="collect_surname",
        role_messages=[{
            "role": "system",
            "content": "Raccogli il cognome del paziente per finalizzare la prenotazione."
        }],
        task_messages=[{
            "role": "system",
            "content": "Qual è il tuo cognome?"
        }],
        functions=[
            FlowsFunctionSchema(
                name="collect_surname",
                handler=collect_surname_and_transition,
                description="Raccogli il cognome del paziente",
                properties={
                    "surname": {
                        "type": "string",
                        "description": "Cognome del paziente"
                    }
                },
                required=["surname"]
            )
        ]
    )


def create_collect_phone_node() -> NodeConfig:
    """Create phone number collection node"""
    return NodeConfig(
        name="collect_phone",
        role_messages=[{
            "role": "system",
            "content": "Raccogli il numero di telefono del paziente. Chiedigli di parlare cifra per cifra lentamente per maggiore precisione."
        }],
        task_messages=[{
            "role": "system",
            "content": "Puoi dirmi se il telefono da cui stai chiamando corrisponde a quello ufficiale? Se no, dimmi il tuo numero di telefono cifra per cifra. Lentamente!"
        }],
        functions=[
            FlowsFunctionSchema(
                name="collect_phone",
                handler=collect_phone_and_transition,
                description="Raccogli il numero di telefono del paziente",
                properties={
                    "phone": {
                        "type": "string",
                        "description": "Numero di telefono del paziente"
                    }
                },
                required=["phone"]
            )
        ]
    )


def create_collect_email_node() -> NodeConfig:
    """Create email collection node with improved prompting for full email capture"""
    return NodeConfig(
        name="collect_email",
        role_messages=[{
            "role": "system",
            "content": "Raccogli l'indirizzo email completo del paziente. Chiedigli di leggere l'intera email, lentamente e chiaramente. Conferma ripetendo l'email che hai sentito."
        }],
        task_messages=[{
            "role": "system",
            "content": "Puoi dirmi la tua email completa? Per favore dilla lentamente e chiaramente."
        }],
        functions=[
            FlowsFunctionSchema(
                name="collect_email",
                handler=collect_email_and_transition,
                description="Raccogli l'indirizzo email completo del paziente",
                properties={
                    "email": {
                        "type": "string",
                        "description": "Indirizzo email completo del paziente (es: nome@dominio.com)"
                    }
                },
                required=["email"]
            )
        ]
    )



def create_collect_reminder_authorization_node() -> NodeConfig:
    """Create reminder authorization collection node"""
    return NodeConfig(
        name="collect_reminder_authorization",
        role_messages=[{
            "role": "system",
            "content": "Chiedi se il paziente vuole ricevere promemoria via email per il suo appuntamento."
        }],
        task_messages=[{
            "role": "system",
            "content": "Vorresti ricevere un'email che ti ricordi quando è il tuo appuntamento programmato?"
        }],
        functions=[
            FlowsFunctionSchema(
                name="collect_reminder_authorization",
                handler=collect_reminder_authorization_and_transition,
                description="Raccogli la preferenza per l'autorizzazione ai promemoria",
                properties={
                    "reminder_authorization": {
                        "type": "boolean",
                        "description": "Se il paziente vuole ricevere promemoria per l'appuntamento (vero/falso)"
                    }
                },
                required=["reminder_authorization"]
            )
        ]
    )


def create_collect_marketing_authorization_node() -> NodeConfig:
    """Create marketing authorization collection node"""
    return NodeConfig(
        name="collect_marketing_authorization",
        role_messages=[{
            "role": "system",
            "content": "Chiedi se il paziente vuole ricevere aggiornamenti di marketing da Cerba HealthCare."
        }],
        task_messages=[{
            "role": "system",
            "content": "Vuoi ricevere aggiornamenti su Cerba HealthCare?"
        }],
        functions=[
            FlowsFunctionSchema(
                name="collect_marketing_authorization",
                handler=collect_marketing_authorization_and_transition,
                description="Raccogli la preferenza per l'autorizzazione al marketing",
                properties={
                    "marketing_authorization": {
                        "type": "boolean",
                        "description": "Se il paziente vuole ricevere aggiornamenti di marketing (vero/falso)"
                    }
                },
                required=["marketing_authorization"]
            )
        ]
    )


def create_confirm_patient_details_node(patient_details: dict) -> NodeConfig:
    """Create patient details confirmation node (without fiscal code display)"""
    details_summary = f"""Questi dettagli sono corretti?

Nome: {patient_details.get('name', '')}
Cognome: {patient_details.get('surname', '')}
Numero di telefono: {patient_details.get('phone', '')}
Email: {patient_details.get('email', '')}"""

    return NodeConfig(
        name="confirm_patient_details",
        role_messages=[{
            "role": "system",
            "content": "Present the collected patient details for confirmation before finalizing the booking."
        }],
        task_messages=[{
            "role": "system",
            "content": details_summary
        }],
        functions=[
            FlowsFunctionSchema(
                name="confirm_details",
                handler=confirm_details_and_create_booking,
                description="Confirm the collected patient details",
                properties={
                    "details_confirmed": {
                        "type": "boolean",
                        "description": "Whether the patient confirms the details are correct (true/false)"
                    }
                },
                required=["details_confirmed"]
            )
        ]
    )




def create_confirm_email_node(email: str) -> NodeConfig:
    """Create email confirmation node"""
    from flows.handlers.patient_detail_handlers import confirm_email_and_transition
    return NodeConfig(
        name="confirm_email",
        role_messages=[{
            "role": "system",
            "content": "Fornisci l'indirizzo email per conferma e chiedi se è corretto."
        }],
        task_messages=[{
            "role": "system", 
            "content": f"Ho la tua email come: {email}. È corretto? Di' \"sì\" se è corretto, o \"cambia\" se vuoi fornire un'email diversa."
        }],
        functions=[
            FlowsFunctionSchema(
                name="confirm_email",
                handler=confirm_email_and_transition,
                description="Confirm the email address or request to change it",
                properties={
                    "action": {
                        "type": "string",
                        "enum": ["confirm", "change"],
                        "description": "confirm if email is correct, change if user wants to modify it"
                    }
                },
                required=["action"]
            )
        ]
    )



