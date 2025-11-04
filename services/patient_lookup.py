"""
Patient Lookup Service
Handles phone+DOB normalization and patient disambiguation for existing records
"""

import re
from typing import Dict, Any, Optional, List
from loguru import logger


# In-memory patient store for test mode
PATIENTS_DB = [
    {
        "id": "p1",
        "phone": "+393333319326",
        "first_name": "Rudy",
        "last_name": "Crapella",
        "dob": "1979-06-19",
        "fiscal_code": "FC10001",
        "email": "rudy.crapella@gmail.com"
    },
    {
        "id": "p2",
        "phone": "+393336164267",
        "first_name": "Steffano",
        "last_name": "Tacchi",
        "dob": "1990-01-01",
        "fiscal_code": "FC20002",
        "email": "stefano.tacchi@cerbahealthcare.it"
    },
    {
        "id": "p3",
        "phone": "+393333319326",
        "first_name": "Rudy Son",
        "last_name": "Krsip",
        "dob": "1985-03-01",
        "fiscal_code": "FC10003",
        "email": "rudy.son@gmail.com"
    }
]


def normalize_phone(raw: str) -> Optional[str]:
    """
    Normalize phone number to consistent +country format

    Args:
        raw: Raw phone number from various sources

    Returns:
        Normalized phone number or None if unparseable
    """
    if not raw:
        return None

    # Remove all non-digit characters
    digits_only = re.sub(r'[^\d]', '', raw.strip())

    if not digits_only:
        return None

    # Handle Italian numbers
    if digits_only.startswith('39'):
        # Already has country code
        return f"+{digits_only}"
    elif digits_only.startswith('3'):
        # Missing country code, add Italian +39
        return f"+39{digits_only}"
    elif len(digits_only) >= 10:
        # Assume it's a complete number, add +39 if reasonable length
        return f"+39{digits_only}"

    # If we can't determine format, return None
    logger.warning(f"📞 Could not normalize phone: {raw}")
    return None


def normalize_dob(raw: str) -> Optional[str]:
    """
    Normalize date of birth to YYYY-MM-DD format

    Args:
        raw: Raw date string

    Returns:
        Normalized date in YYYY-MM-DD format or None
    """
    if not raw:
        return None

    # If already in YYYY-MM-DD format
    if re.match(r'^\d{4}-\d{2}-\d{2}$', raw.strip()):
        return raw.strip()

    # Add more date format handling if needed
    # For now, return as-is if it passes basic validation
    return raw.strip()




def get_patient_id_for_logging(patient: Dict[str, Any]) -> str:
    """
    Get safe patient identifier for logging

    Args:
        patient: Patient record

    Returns:
        Safe patient ID for logging
    """
    return patient.get('id', 'unknown')


def lookup_by_phone_and_dob(phone: str, dob: str) -> Optional[Dict[str, Any]]:
    """
    Find patient record by phone number and date of birth

    Args:
        phone: Caller's phone number (any format)
        dob: Date of birth (any reasonable format)

    Returns:
        Matching patient record or None if not found
    """
    normalized_phone = normalize_phone(phone)
    normalized_dob = normalize_dob(dob)

    if not normalized_phone or not normalized_dob:
        logger.warning(f"📞 Lookup failed: invalid phone ({phone or ''}) or DOB")
        return None

    logger.info(f"🔍 Looking up patient: phone={normalized_phone}, dob={normalized_dob}")

    # Search through patients database
    for patient in PATIENTS_DB:
        patient_phone = normalize_phone(patient.get('phone', ''))
        patient_dob = normalize_dob(patient.get('dob', ''))

        if patient_phone == normalized_phone and patient_dob == normalized_dob:
            patient_id = get_patient_id_for_logging(patient)
            logger.success(f"✅ Patient found: ID={patient_id}, name={patient.get('first_name', '')} {patient.get('last_name', '')}")
            return patient.copy()  # Return copy to avoid accidental modifications

    logger.info(f"❌ No patient found for phone={normalized_phone}")
    return None


def populate_patient_state(flow_manager, patient: Dict[str, Any]) -> None:
    """
    Populate flow manager state with patient data from lookup

    Args:
        flow_manager: Pipecat flow manager instance
        patient: Patient record from database
    """
    if not patient:
        return

    # Combine first and last name into full_name
    first_name = patient.get('first_name', '')
    last_name = patient.get('last_name', '')
    full_name = f"{first_name} {last_name}".strip()

    # Populate all patient fields in state
    flow_manager.state.update({
        "patient_full_name": full_name,  # Store combined full name
        "patient_phone": patient.get('phone', ''),
        "patient_email": patient.get('email', ''),
        "generated_fiscal_code": patient.get('fiscal_code', ''),
        "patient_found_in_db": True,
        "patient_db_id": patient.get('id', '')
    })

    patient_id = get_patient_id_for_logging(patient)
    logger.success(f"✅ Patient state populated for ID={patient_id}")


def get_patient_summary_text(patient: Dict[str, Any]) -> str:
    """
    Generate summary text for patient confirmation

    Args:
        patient: Patient record

    Returns:
        Formatted summary text for phone verification only
    """
    return f"""Perfect! We found your details in our Cerba Healthcare database and can proceed without collecting your personal information again.

We have your information in our database and we will message the booking confirmation text to the phone number from where you are calling right now. Should we proceed or you need to change the phone number?"""


# Global patient lookup service instance
patient_lookup_service = {
    'normalize_phone': normalize_phone,
    'normalize_dob': normalize_dob,
    'lookup_by_phone_and_dob': lookup_by_phone_and_dob,
    'populate_patient_state': populate_patient_state,
    'get_patient_summary_text': get_patient_summary_text,
    'get_patient_id_for_logging': get_patient_id_for_logging
}