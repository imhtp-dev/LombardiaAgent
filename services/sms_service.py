"""
Twilio SMS Service for Healthcare Booking Confirmations
Handles sending booking confirmation SMS to Italian phone numbers with GDPR compliance
"""

import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class SMSMessage:
    """SMS message data structure"""
    to_phone: str
    message_body: str
    booking_id: str
    patient_name: str
    metadata: Dict[str, Any] = None

@dataclass
class SMSResponse:
    """SMS delivery response"""
    success: bool
    message_sid: Optional[str] = None
    error_message: Optional[str] = None
    delivery_status: Optional[str] = None

class TwilioSMSService:
    """
    Twilio SMS service for healthcare booking confirmations in Italy
    Handles GDPR compliance, delivery tracking, and error handling
    """

    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_phone = os.getenv("TWILIO_PHONE_NUMBER")

        # Validate configuration
        self._validate_config()

        # Initialize Twilio client (will be imported when needed)
        self.client = None

    def _validate_config(self) -> None:
        """Validate Twilio configuration"""
        required_vars = [
            ("TWILIO_ACCOUNT_SID", self.account_sid),
            ("TWILIO_AUTH_TOKEN", self.auth_token),
            ("TWILIO_PHONE_NUMBER", self.from_phone)
        ]

        missing_vars = [name for name, value in required_vars if not value]

        if missing_vars:
            raise ValueError(f"Missing Twilio environment variables: {', '.join(missing_vars)}")

        logger.info(f"✅ Twilio SMS service configured with number: {self.from_phone}")

    def _get_twilio_client(self):
        """Get or create Twilio client instance"""
        if self.client is None:
            try:
                from twilio.rest import Client
                self.client = Client(self.account_sid, self.auth_token)
                logger.debug("📱 Twilio client initialized")
            except ImportError:
                raise ImportError("Twilio package not installed. Run: pip install twilio")
            except Exception as e:
                raise Exception(f"Failed to initialize Twilio client: {e}")

        return self.client

    def _normalize_italian_phone(self, phone: str) -> str:
        """
        Normalize Italian phone number for SMS delivery

        Args:
            phone: Phone number in various formats

        Returns:
            Normalized phone number with +39 country code
        """
        if not phone:
            raise ValueError("Phone number is required")

        # Remove all non-digit characters except +
        clean_phone = ''.join(c for c in phone if c.isdigit() or c == '+')

        # Handle different Italian number formats
        if clean_phone.startswith('+39'):
            return clean_phone
        elif clean_phone.startswith('39') and len(clean_phone) >= 12:
            return f'+{clean_phone}'
        elif clean_phone.startswith('3') and len(clean_phone) == 10:
            return f'+39{clean_phone}'
        else:
            # Assume it's a local Italian number
            return f'+39{clean_phone}'

    def _create_booking_confirmation_message(self, booking_data: Dict[str, Any]) -> str:
        """
        Create Italian healthcare booking confirmation message

        Args:
            booking_data: Booking information

        Returns:
            Formatted SMS message in Italian
        """
        # Extract booking details
        patient_name = booking_data.get('patient_name', 'Paziente')
        service_name = booking_data.get('service_name', 'Servizio')
        center_name = booking_data.get('center_name', 'Centro medico')
        booking_date = booking_data.get('booking_date', 'Data da confermare')
        booking_time = booking_data.get('booking_time', 'Orario da confermare')
        booking_id = booking_data.get('booking_id', 'N/A')

        # Format the message (keep under 160 characters for single SMS)
        message = f"""🏥 Cerba Healthcare - Conferma Prenotazione

Gentile {patient_name},
La sua prenotazione è confermata:

📋 Servizio: {service_name}
📍 Centro: {center_name}
📅 Data: {booking_date}
🕐 Ora: {booking_time}

Codice: {booking_id}

Per modifiche: +39 02 xxxxx
Per annullare rispondi STOP

Cerba Healthcare"""

        return message

    async def send_booking_confirmation(self, booking_data: Dict[str, Any]) -> SMSResponse:
        """
        Send booking confirmation SMS asynchronously

        Args:
            booking_data: Dictionary containing booking information
                - patient_name: str
                - patient_phone: str
                - service_name: str
                - center_name: str
                - booking_date: str
                - booking_time: str
                - booking_id: str

        Returns:
            SMSResponse with delivery status
        """
        try:
            # Validate and normalize phone number
            patient_phone = booking_data.get('patient_phone')
            if not patient_phone:
                return SMSResponse(
                    success=False,
                    error_message="Patient phone number is required"
                )

            normalized_phone = self._normalize_italian_phone(patient_phone)
            logger.info(f"📱 Sending booking confirmation SMS to: {normalized_phone}")

            # Create message content
            message_body = self._create_booking_confirmation_message(booking_data)

            # Get Twilio client
            client = self._get_twilio_client()

            # Send SMS using Twilio (in thread to avoid blocking)
            loop = asyncio.get_event_loop()
            message = await loop.run_in_executor(
                None,
                lambda: client.messages.create(
                    body=message_body,
                    from_=self.from_phone,
                    to=normalized_phone,
                    # Optional: Add status callback for delivery tracking
                    # status_callback='https://your-domain.com/sms-status'
                )
            )

            logger.success(f"✅ SMS sent successfully! SID: {message.sid}")

            return SMSResponse(
                success=True,
                message_sid=message.sid,
                delivery_status=message.status
            )

        except Exception as e:
            error_msg = f"Failed to send SMS: {str(e)}"
            logger.error(f"❌ {error_msg}")

            return SMSResponse(
                success=False,
                error_message=error_msg
            )

    def send_booking_confirmation_sync(self, booking_data: Dict[str, Any]) -> SMSResponse:
        """
        Send booking confirmation SMS synchronously (for non-async contexts)

        Args:
            booking_data: Dictionary containing booking information

        Returns:
            SMSResponse with delivery status
        """
        try:
            # Validate and normalize phone number
            patient_phone = booking_data.get('patient_phone')
            if not patient_phone:
                return SMSResponse(
                    success=False,
                    error_message="Patient phone number is required"
                )

            normalized_phone = self._normalize_italian_phone(patient_phone)
            logger.info(f"📱 Sending booking confirmation SMS to: {normalized_phone}")

            # Create message content
            message_body = self._create_booking_confirmation_message(booking_data)

            # Get Twilio client
            client = self._get_twilio_client()

            # Send SMS using Twilio
            message = client.messages.create(
                body=message_body,
                from_=self.from_phone,
                to=normalized_phone
            )

            logger.success(f"✅ SMS sent successfully! SID: {message.sid}")

            return SMSResponse(
                success=True,
                message_sid=message.sid,
                delivery_status=message.status
            )

        except Exception as e:
            error_msg = f"Failed to send SMS: {str(e)}"
            logger.error(f"❌ {error_msg}")

            return SMSResponse(
                success=False,
                error_message=error_msg
            )

    async def get_delivery_status(self, message_sid: str) -> Dict[str, Any]:
        """
        Get SMS delivery status from Twilio

        Args:
            message_sid: Twilio message SID

        Returns:
            Dictionary with delivery status information
        """
        try:
            client = self._get_twilio_client()

            loop = asyncio.get_event_loop()
            message = await loop.run_in_executor(
                None,
                lambda: client.messages(message_sid).fetch()
            )

            return {
                "sid": message.sid,
                "status": message.status,
                "error_code": message.error_code,
                "error_message": message.error_message,
                "date_sent": message.date_sent,
                "date_updated": message.date_updated
            }

        except Exception as e:
            logger.error(f"Failed to get delivery status: {e}")
            return {"error": str(e)}

# Global SMS service instance
sms_service = TwilioSMSService()

# Convenience functions for easy import
async def send_booking_confirmation_sms(booking_data: Dict[str, Any]) -> SMSResponse:
    """Send booking confirmation SMS (async)"""
    return await sms_service.send_booking_confirmation(booking_data)

def send_booking_confirmation_sms_sync(booking_data: Dict[str, Any]) -> SMSResponse:
    """Send booking confirmation SMS (sync)"""
    return sms_service.send_booking_confirmation_sync(booking_data)