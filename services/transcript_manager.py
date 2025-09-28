"""
Transcript Manager for recording conversation transcripts and generating summaries
"""

import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger

from services.call_storage import CallDataStorage


@dataclass
class TranscriptMessage:
    """Represents a single message in the conversation transcript"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None


class TranscriptManager:
    """Manages conversation transcripts and call data extraction"""

    def __init__(self):
        self.conversation_log: List[TranscriptMessage] = []
        self.session_start_time: Optional[datetime] = None
        self.session_id: Optional[str] = None
        self.storage: Optional[CallDataStorage] = None

        # Initialize Azure storage
        try:
            self.storage = CallDataStorage()
        except Exception as e:
            logger.error(f"❌ Failed to initialize storage: {e}")
            self.storage = None

    def start_session(self, session_id: str) -> None:
        """Start a new conversation session"""
        self.session_id = session_id
        self.session_start_time = datetime.now()
        self.conversation_log.clear()
        logger.info(f"📝 Started transcript recording for session: {session_id}")

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation transcript"""
        if not content.strip():
            return

        timestamp = datetime.now().isoformat()
        message = TranscriptMessage(
            role=role,
            content=content.strip(),
            timestamp=timestamp
        )

        self.conversation_log.append(message)
        logger.debug(f"📝 Added {role} message: {content[:100]}{'...' if len(content) > 100 else ''}")

    def add_user_message(self, content: str) -> None:
        """Add a user message to transcript"""
        self.add_message("user", content)

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to transcript"""
        self.add_message("assistant", content)

    def get_conversation_duration(self) -> int:
        """Get conversation duration in seconds"""
        if not self.session_start_time:
            return 0
        return int((datetime.now() - self.session_start_time).total_seconds())

    def generate_conversation_summary(self) -> str:
        """Generate a basic conversation summary"""
        if not self.conversation_log:
            return "No conversation recorded."

        user_messages = [msg for msg in self.conversation_log if msg.role == "user"]
        assistant_messages = [msg for msg in self.conversation_log if msg.role == "assistant"]

        # Basic summary template
        summary_parts = []

        if user_messages:
            summary_parts.append(f"User sent {len(user_messages)} messages")

        if assistant_messages:
            summary_parts.append(f"Assistant sent {len(assistant_messages)} messages")

        duration = self.get_conversation_duration()
        if duration > 0:
            summary_parts.append(f"Call duration: {duration} seconds")

        # Try to extract key information from the conversation
        conversation_text = " ".join([msg.content for msg in self.conversation_log])

        key_info = []
        if "prenotazione" in conversation_text.lower() or "booking" in conversation_text.lower():
            key_info.append("Booking-related conversation")

        if "nome" in conversation_text.lower() or "name" in conversation_text.lower():
            key_info.append("Personal information collected")

        if "email" in conversation_text.lower():
            key_info.append("Email address provided")

        if key_info:
            summary_parts.extend(key_info)

        return ". ".join(summary_parts) + "."

    async def generate_ai_summary(self, flow_manager=None) -> str:
        """Generate AI-powered conversation summary using OpenAI"""
        try:
            if not self.conversation_log:
                return "No conversation to summarize."

            # Create conversation text for summarization
            conversation_text = "\n".join([
                f"{msg.role.title()}: {msg.content}"
                for msg in self.conversation_log
            ])

            # Simple summary prompt
            summary_prompt = f"""Summarize this healthcare booking conversation in Italian. Focus on:
- Patient information collected
- Services requested
- Booking status
- Any important details

Conversation:
{conversation_text}

Summary (in Italian, max 200 words):"""

            # If we have access to flow manager and LLM, use it for better summary
            if flow_manager and hasattr(flow_manager, 'llm'):
                try:
                    # This would need to be implemented based on your LLM service structure
                    # For now, return basic summary
                    logger.debug("🤖 AI summary generation not implemented yet, using basic summary")
                    return self.generate_conversation_summary()
                except Exception as e:
                    logger.error(f"❌ AI summary generation failed: {e}")
                    return self.generate_conversation_summary()
            else:
                return self.generate_conversation_summary()

        except Exception as e:
            logger.error(f"❌ Error generating summary: {e}")
            return self.generate_conversation_summary()

    async def extract_and_store_call_data(self, flow_manager) -> bool:
        """Extract all call data and store in Azure Storage"""
        try:
            if not self.session_id:
                logger.error("❌ No session ID available for storage")
                return False

            logger.info(f"📊 Extracting call data for session: {self.session_id}")

            # Generate conversation summary
            summary = await self.generate_ai_summary(flow_manager)

            # Extract patient data from flow manager state
            patient_data = {
                "name": flow_manager.state.get("patient_name", ""),
                "surname": flow_manager.state.get("patient_surname", ""),
                "birth_date": flow_manager.state.get("patient_dob", ""),
                "gender": flow_manager.state.get("patient_gender", ""),
                "birth_city": flow_manager.state.get("patient_birth_city", ""),
                "address": flow_manager.state.get("patient_address", ""),
                "phone": flow_manager.state.get("patient_phone", ""),
                "email": flow_manager.state.get("patient_email", "")
            }

            # Extract booking data if available
            booking_data = {
                "booking_code": flow_manager.state.get("final_booking", {}).get("code", ""),
                "booking_uuid": flow_manager.state.get("final_booking", {}).get("uuid", ""),
                "selected_services": flow_manager.state.get("selected_services", []),
                "booked_slots": flow_manager.state.get("booked_slots", [])
            }

            # Prepare complete call data
            call_data = {
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "call_start_time": self.session_start_time.isoformat() if self.session_start_time else None,
                "call_duration_seconds": self.get_conversation_duration(),

                # Generated fiscal code
                "fiscal_code": flow_manager.state.get("generated_fiscal_code", ""),
                "fiscal_code_generation_data": flow_manager.state.get("fiscal_code_generation_data", {}),
                "fiscal_code_error": flow_manager.state.get("fiscal_code_error", ""),

                # Patient information
                "patient_data": patient_data,

                # Booking information
                "booking_data": booking_data,

                # Conversation data
                "transcript": [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp
                    }
                    for msg in self.conversation_log
                ],
                "summary": summary,
                "total_messages": len(self.conversation_log),
                "user_messages": len([msg for msg in self.conversation_log if msg.role == "user"]),
                "assistant_messages": len([msg for msg in self.conversation_log if msg.role == "assistant"]),

                # Authorizations
                "reminder_authorization": flow_manager.state.get("reminder_authorization", False),
                "marketing_authorization": flow_manager.state.get("marketing_authorization", False)
            }

            # Store in Azure Storage
            if self.storage:
                blob_name = await self.storage.store_call_data(self.session_id, call_data)
                logger.success(f"✅ Call data stored successfully: {blob_name}")

                # Also store fiscal code separately if generated
                fiscal_code = call_data.get("fiscal_code")
                if fiscal_code:
                    await self.storage.store_fiscal_code_only(
                        self.session_id,
                        fiscal_code,
                        patient_data
                    )

                return True
            else:
                logger.error("❌ Storage not available")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to extract and store call data: {e}")
            return False

    def get_transcript_json(self) -> str:
        """Get transcript as JSON string"""
        return json.dumps([
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp
            }
            for msg in self.conversation_log
        ], ensure_ascii=False, indent=2)

    def clear_session(self) -> None:
        """Clear current session data"""
        self.conversation_log.clear()
        self.session_id = None
        self.session_start_time = None
        logger.info("🗑️ Transcript session cleared")


# Global transcript manager instance
transcript_manager = TranscriptManager()