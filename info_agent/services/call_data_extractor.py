"""
Call Data Extractor Service
Extracts call data and saves to tb_stat table in Supabase
Based on PDF documentation
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger

from info_agent.api.database import db


class CallDataExtractor:
    """Extract and store call data to tb_stat table"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.call_id = str(uuid.uuid4())
        self.started_at = None
        self.ended_at = None
        self.transcript = []
        self.llm_token_count = 0
        self.assistant_id = "pipecat-piemonte-001"  # Default Piedmont assistant
        
        logger.info(f"📊 Call data extractor initialized for session: {session_id}")
        logger.info(f"📞 Call ID: {self.call_id}")
    
    def start_call(self, caller_phone: Optional[str] = None, interaction_id: Optional[str] = None):
        """Mark call start time"""
        self.started_at = datetime.now()
        self.caller_phone = caller_phone
        self.interaction_id = interaction_id
        logger.info(f"⏱️ Call started at: {self.started_at}")
    
    def end_call(self):
        """Mark call end time"""
        self.ended_at = datetime.now()
        logger.info(f"⏱️ Call ended at: {self.ended_at}")
    
    def add_transcript_entry(self, role: str, content: str):
        """Add entry to transcript"""
        self.transcript.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def increment_tokens(self, tokens: int):
        """Track LLM token usage"""
        self.llm_token_count += tokens
    
    def _calculate_duration(self) -> Optional[float]:
        """Calculate call duration in seconds"""
        if self.started_at and self.ended_at:
            delta = self.ended_at - self.started_at
            return delta.total_seconds()
        return None
    
    def _calculate_cost(self, duration_seconds: Optional[float]) -> Optional[float]:
        """Calculate call cost (seconds × 0.006)"""
        if duration_seconds:
            return round(duration_seconds * 0.006, 4)
        return None
    
    def _determine_action(self, flow_state: Dict[str, Any]) -> str:
        """
        Determine action type based on flow state
        Values: completed, question, transfer, book
        """
        if flow_state.get("transfer_requested"):
            transfer_reason = flow_state.get("transfer_reason", "").lower()
            if "unknown" in transfer_reason or "don't know" in transfer_reason:
                return "question"
            elif "book" in transfer_reason:
                return "book"
            else:
                return "transfer"
        
        # Check if info was provided successfully
        functions_called = flow_state.get("functions_called", [])
        if functions_called:
            return "completed"
        
        return "completed"
    
    def _determine_sentiment(self, flow_state: Dict[str, Any], summary: str) -> str:
        """
        Determine sentiment from conversation
        Values: positive, negative, neutral, N/A
        """
        # Check if transfer was requested (usually negative)
        if flow_state.get("transfer_requested"):
            transfer_reason = flow_state.get("transfer_reason", "").lower()
            if "frustrat" in transfer_reason or "angry" in transfer_reason:
                return "negative"
            return "neutral"
        
        # Check if functions were called successfully
        functions_called = flow_state.get("functions_called", [])
        if functions_called:
            # If info was provided, likely positive
            return "positive"
        
        # Try to analyze summary for sentiment keywords
        if summary:
            summary_lower = summary.lower()
            positive_words = ["grazie", "perfetto", "ottimo", "bene", "soddisfatto"]
            negative_words = ["problema", "male", "pessimo", "frustrato", "arrabbiato"]
            
            positive_count = sum(1 for word in positive_words if word in summary_lower)
            negative_count = sum(1 for word in negative_words if word in summary_lower)
            
            if positive_count > negative_count:
                return "positive"
            elif negative_count > positive_count:
                return "negative"
        
        return "neutral"
    
    def _determine_esito_chiamata(self, flow_state: Dict[str, Any]) -> str:
        """
        Determine call outcome
        Values: COMPLETATA, TRASFERITA, NON COMPLETATA
        """
        if flow_state.get("transfer_requested"):
            return "TRASFERITA"
        
        # Check if conversation ended naturally
        final_node = flow_state.get("current_node", "")
        if final_node == "goodbye" or flow_state.get("conversation_ended"):
            return "COMPLETATA"
        
        # If call ended abruptly (no goodbye)
        functions_called = flow_state.get("functions_called", [])
        if functions_called:
            return "COMPLETATA"
        
        # Patient likely ended call prematurely
        return "NON COMPLETATA"
    
    def _determine_motivazione(self, flow_state: Dict[str, Any], action: str) -> str:
        """
        Determine call motivation/reason
        Values: Info fornite, Argomento sconosciuto, Interrotta dal paziente, 
                Prenotazione, Mancata comprensione, Richiesta paziente
        """
        if action == "completed":
            return "Info fornite"
        elif action == "question":
            return "Argomento sconosciuto"
        elif action == "book":
            return "Prenotazione"
        elif action == "transfer":
            transfer_reason = flow_state.get("transfer_reason", "").lower()
            if "understand" in transfer_reason or "comprens" in transfer_reason:
                return "Mancata comprensione"
            else:
                return "Richiesta paziente"
        
        # Check if patient interrupted
        if flow_state.get("user_interrupted"):
            return "Interrotta dal paziente"
        
        return "Info fornite"
    
    def _extract_patient_intent(self, flow_state: Dict[str, Any]) -> Optional[str]:
        """
        Extract brief summary of patient's intent
        """
        # Get functions that were called
        functions_called = flow_state.get("functions_called", [])
        if functions_called:
            intent_parts = []
            
            for func in functions_called:
                if "knowledge" in func:
                    intent_parts.append("richiesta informazioni generali")
                elif "price" in func:
                    intent_parts.append("richiesta prezzi visite")
                elif "exam" in func:
                    intent_parts.append("informazioni su esami richiesti")
                elif "clinic" in func:
                    intent_parts.append("informazioni su orari/sede")
            
            if intent_parts:
                return "; ".join(intent_parts)
        
        # Check transfer reason
        if flow_state.get("transfer_requested"):
            transfer_reason = flow_state.get("transfer_reason", "")
            if transfer_reason:
                return f"Richiesta trasferimento: {transfer_reason}"
        
        return "Richiesta informazioni mediche"
    
    def _generate_transcript_text(self) -> str:
        """Generate formatted transcript text"""
        if not self.transcript:
            return ""
        
        lines = []
        for entry in self.transcript:
            role = "Paziente" if entry["role"] == "user" else "Assistente"
            lines.append(f"[{role}]: {entry['content']}")
        
        return "\n".join(lines)
    
    def _generate_summary(self, flow_state: Dict[str, Any], patient_intent: str) -> str:
        """Generate AI summary of the call"""
        # For now, create a structured summary
        # In future, could use LLM to generate more natural summary
        
        action = self._determine_action(flow_state)
        esito = self._determine_esito_chiamata(flow_state)
        
        summary_parts = [
            f"Chiamata {esito.lower()}.",
            f"Paziente ha richiesto: {patient_intent}.",
        ]
        
        if action == "completed":
            summary_parts.append("Informazioni fornite con successo dall'assistente vocale.")
        elif action == "transfer":
            transfer_reason = flow_state.get("transfer_reason", "richiesta del paziente")
            summary_parts.append(f"Chiamata trasferita a operatore umano per: {transfer_reason}.")
        elif action == "question":
            summary_parts.append("Argomento sconosciuto, trasferita a operatore per assistenza.")
        
        functions_called = flow_state.get("functions_called", [])
        if functions_called:
            summary_parts.append(f"Funzioni utilizzate: {', '.join(functions_called)}.")
        
        return " ".join(summary_parts)
    
    async def save_to_database(self, flow_state: Dict[str, Any]) -> bool:
        """
        Extract all data and save to tb_stat table
        
        Args:
            flow_state: Flow manager state containing call information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"💾 Extracting call data for session: {self.session_id}")
            
            # Calculate basic metrics
            duration_seconds = self._calculate_duration()
            cost = self._calculate_cost(duration_seconds)
            
            # Determine call attributes
            action = self._determine_action(flow_state)
            esito_chiamata = self._determine_esito_chiamata(flow_state)
            patient_intent = self._extract_patient_intent(flow_state)
            sentiment = self._determine_sentiment(flow_state, "")
            motivazione = self._determine_motivazione(flow_state, action)
            
            # Generate transcript and summary
            transcript_text = self._generate_transcript_text()
            summary = self._generate_summary(flow_state, patient_intent or "N/A")
            
            # Re-calculate sentiment with summary
            sentiment = self._determine_sentiment(flow_state, summary)
            
            # Get phone number
            phone_number = flow_state.get("caller_phone") or self.caller_phone
            
            logger.info(f"📊 Call Data Summary:")
            logger.info(f"   Call ID: {self.call_id}")
            logger.info(f"   Duration: {duration_seconds:.2f}s" if duration_seconds else "   Duration: N/A")
            logger.info(f"   Cost: ${cost:.4f}" if cost else "   Cost: N/A")
            logger.info(f"   Action: {action}")
            logger.info(f"   Sentiment: {sentiment}")
            logger.info(f"   Esito: {esito_chiamata}")
            logger.info(f"   Motivazione: {motivazione}")
            logger.info(f"   Phone: {phone_number or 'N/A'}")
            logger.info(f"   LLM Tokens: {self.llm_token_count}")
            
            # Insert into database
            query = """
            INSERT INTO tb_stat (
                call_id, phone_number, assistant_id, started_at, ended_at,
                duration_seconds, action, sentiment, esito_chiamata, motivazione,
                patient_intent, transcript, summary, cost, llm_token,
                service, interaction_id
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17
            )
            """
            
            await db.execute(
                query,
                self.call_id,
                phone_number,
                self.assistant_id,
                self.started_at,
                self.ended_at,
                duration_seconds,
                action,
                sentiment,
                esito_chiamata,
                motivazione,
                patient_intent,
                transcript_text,
                summary,
                cost,
                self.llm_token_count,
                "pipecat",
                self.interaction_id
            )
            
            logger.success(f"✅ Call data saved to tb_stat table")
            logger.info(f"   Database Call ID: {self.call_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving call data to database: {e}")
            import traceback
            traceback.print_exc()
            return False


# Global storage for active extractors
_active_extractors: Dict[str, CallDataExtractor] = {}


def get_call_extractor(session_id: str) -> CallDataExtractor:
    """Get or create call data extractor for session"""
    if session_id not in _active_extractors:
        _active_extractors[session_id] = CallDataExtractor(session_id)
    return _active_extractors[session_id]


def cleanup_call_extractor(session_id: str):
    """Remove call data extractor for session"""
    if session_id in _active_extractors:
        del _active_extractors[session_id]
        logger.debug(f"🧹 Cleaned up call extractor for session: {session_id}")
