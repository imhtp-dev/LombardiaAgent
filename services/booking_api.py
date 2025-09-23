"""
Booking API service for creating final bookings with patient details
"""

import requests
from typing import Dict, Any
from loguru import logger

from services.config import config
from services.auth import auth_service


def create_booking(booking_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a booking using the POST amb/booking API

    Args:
        booking_data: Dictionary containing patient info and booking details

    Returns:
        Dictionary with success status and booking details
    """
    try:
        # Get authentication token
        token = auth_service.get_token()

        if not token:
            logger.error("Failed to get authentication token")
            return {
                "success": False,
                "message": "Authentication failed",
                "booking": None
            }

        # API endpoint
        url = f"{config.CERBA_BASE_URL}/amb/booking"

        # Headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        logger.info(f"Creating booking at: {url}")
        logger.debug(f"Booking data: {booking_data}")

        # Make POST request
        response = requests.post(
            url,
            json=booking_data,
            headers=headers,
            timeout=config.REQUEST_TIMEOUT
        )

        logger.info(f"Booking API response status: {response.status_code}")

        # Handle response
        if response.status_code == 200 or response.status_code == 201:
            booking_response = response.json()

            # Check if response is a list (as per API documentation)
            if isinstance(booking_response, list) and len(booking_response) > 0:
                booking_info = booking_response[0]
            else:
                booking_info = booking_response

            logger.success(f"✅ Booking created successfully")
            logger.info(f"Booking UUID: {booking_info.get('uuid', 'N/A')}")
            logger.info(f"Booking Code: {booking_info.get('code', 'N/A')}")

            return {
                "success": True,
                "message": "Booking created successfully",
                "booking": booking_info
            }

        elif response.status_code == 400:
            # Bad request - likely validation error
            try:
                error_data = response.json()
                error_message = error_data.get("message", "Invalid booking data")
                logger.error(f"❌ Booking validation error: {error_message}")

                return {
                    "success": False,
                    "message": f"Booking validation failed: {error_message}",
                    "booking": None
                }
            except:
                logger.error(f"❌ Bad request: {response.text}")
                return {
                    "success": False,
                    "message": "Invalid booking data",
                    "booking": None
                }

        elif response.status_code == 401:
            # Authentication error
            logger.error("❌ Authentication failed for booking creation")
            auth_service.clear_token()  # Clear invalid token

            return {
                "success": False,
                "message": "Authentication failed. Please try again.",
                "booking": None
            }

        elif response.status_code == 409:
            # Conflict - likely slot already booked
            try:
                error_data = response.json()
                error_message = error_data.get("message", "Slot no longer available")
                logger.error(f"❌ Booking conflict: {error_message}")

                return {
                    "success": False,
                    "message": "The selected time slot is no longer available",
                    "booking": None
                }
            except:
                logger.error(f"❌ Booking conflict: {response.text}")
                return {
                    "success": False,
                    "message": "The selected time slot is no longer available",
                    "booking": None
                }

        else:
            # Other error
            try:
                error_data = response.json()
                error_message = error_data.get("message", f"HTTP {response.status_code}")
                logger.error(f"❌ Booking API error: {error_message}")

                return {
                    "success": False,
                    "message": f"Booking failed: {error_message}",
                    "booking": None
                }
            except:
                logger.error(f"❌ Booking API error: HTTP {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "message": f"Booking failed: HTTP {response.status_code}",
                    "booking": None
                }

    except requests.exceptions.Timeout:
        logger.error("❌ Booking request timed out")
        return {
            "success": False,
            "message": "Booking request timed out. Please try again.",
            "booking": None
        }

    except requests.exceptions.ConnectionError:
        logger.error("❌ Connection error during booking")
        return {
            "success": False,
            "message": "Connection error. Please check your internet connection.",
            "booking": None
        }

    except Exception as e:
        logger.error(f"❌ Unexpected error during booking: {e}")
        return {
            "success": False,
            "message": "An unexpected error occurred during booking",
            "booking": None
        }


def validate_booking_data(booking_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate booking data before sending to API

    Args:
        booking_data: Booking data to validate

    Returns:
        Dictionary with validation result
    """
    try:
        # Check required patient fields
        patient = booking_data.get("patient", {})
        required_patient_fields = ["name", "surname", "email", "phone", "date_of_birth", "fiscal_code", "gender"]

        for field in required_patient_fields:
            if not patient.get(field):
                return {
                    "valid": False,
                    "message": f"Missing patient {field}"
                }

        # Check booking type
        if not booking_data.get("booking_type"):
            return {
                "valid": False,
                "message": "Missing booking type"
            }

        # Check health services
        health_services = booking_data.get("health_services", [])
        if not health_services or len(health_services) == 0:
            return {
                "valid": False,
                "message": "No health services specified"
            }

        # Check each service has uuid and slot
        for service in health_services:
            if not service.get("uuid"):
                return {
                    "valid": False,
                    "message": "Missing service UUID"
                }
            if not service.get("slot"):
                return {
                    "valid": False,
                    "message": "Missing slot UUID"
                }

        # Check authorization fields
        if "reminder_authorization" not in booking_data:
            return {
                "valid": False,
                "message": "Missing reminder authorization"
            }

        if "marketing_authorization" not in booking_data:
            return {
                "valid": False,
                "message": "Missing marketing authorization"
            }

        return {
            "valid": True,
            "message": "Booking data is valid"
        }

    except Exception as e:
        logger.error(f"Error validating booking data: {e}")
        return {
            "valid": False,
            "message": f"Validation error: {str(e)}"
        }
    

#booking_data = {
    # "patient": {
    #     "name": "MARIO",
    #     "surname": "ROSSI", 
    #     "email": "invictusblaze7@gmail.com",
    #     "phone": "+393333319326",
    #     "date_of_birth": "1980-01-01",
    #     "fiscal_code": "RSSMRA80A01F205X",
    #     "gender": "m"
    # },
    # "booking_type": "private",
    # "health_services": [
    #     {
    #         "uuid": "9a93d65f-396a-45e4-9284-94481bdd2b51",
    #         "slot": "c9ea2bc6-4402-43e8-ada8-0b61af9d5bf8" 
    #     }
    # ],
    # "reminder_authorization": True,
    # "marketing_authorization": False
#}

#result = create_booking(booking_data)
#print(result)

#cmd : cd "/home/cooky/Clients Project/Rudy/Booking Agent Pipecat Flows/pipecat-flows" && python -m services.booking_api