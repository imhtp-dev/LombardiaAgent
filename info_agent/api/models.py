"""
Pydantic models for API requests and responses
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ==================== Authentication Models ====================

class LoginRequest(BaseModel):
    """Login request model"""
    email: EmailStr
    password: str
    remember_me: bool = False


class LoginResponse(BaseModel):
    """Login response model"""
    success: bool
    message: str
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class TokenVerifyResponse(BaseModel):
    """Token verification response"""
    valid: bool
    user: Optional[Dict[str, Any]] = None


# ==================== User Models ====================

class UserCreate(BaseModel):
    """User creation request"""
    nome: str = Field(..., min_length=1)
    cognome: str = Field(..., min_length=1)
    email: EmailStr
    ruolo: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    """User response model"""
    user_id: int
    email: str
    nome: str
    cognome: str
    ruolo: str
    region: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserToggleStatusResponse(BaseModel):
    """User toggle status response"""
    success: bool
    message: str
    new_status: bool


# ==================== Q&A Models ====================

class QACreate(BaseModel):
    """Q&A creation request"""
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    region: str = Field(..., min_length=1)


class QAUpdate(BaseModel):
    """Q&A update request"""
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)


class QAItem(BaseModel):
    """Q&A item response"""
    qa_id: int
    question: str
    answer: str
    region: str
    pinecone_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    id_domanda: Optional[str] = None


class QACreateResponse(BaseModel):
    """Q&A creation response"""
    success: bool
    message: str
    qa_id: int
    pinecone_id: str
    id_domanda: str
    created_by: str
    created_at: str
    updated_at: str
    timezone: str = "UTC+2 (converted to naive for PostgreSQL)"


class QAUpdateResponse(BaseModel):
    """Q&A update response"""
    success: bool
    message: str
    qa_id: int
    old_pinecone_id: str
    new_pinecone_id: str
    updated_by: str
    updated_at: str
    updated_at_timezone: str = "UTC+2"


class QADeleteResponse(BaseModel):
    """Q&A deletion response"""
    success: bool
    message: str
    qa_id: int
    pinecone_id: Optional[str] = None


class QAStatsResponse(BaseModel):
    """Q&A statistics response"""
    region: str
    total_qa: int
    recent_qa: int
    updated_qa: int


# ==================== Dashboard Models ====================

class DashboardStats(BaseModel):
    """Dashboard statistics"""
    total_minutes: int
    total_revenue: float
    total_calls: int
    chart_data: List[Dict[str, Any]]
    avg_duration_minutes: float = 0.0


class CallItem(BaseModel):
    """Call item for list"""
    id: int
    started_at: Optional[datetime]
    call_id: Optional[str]
    interaction_id: Optional[str]
    phone_number: Optional[str]
    duration_seconds: int
    action: str
    sentiment: str
    motivazione: Optional[str]
    esito_chiamata: Optional[str]


class CallListResponse(BaseModel):
    """Call list with pagination"""
    calls: List[Dict[str, Any]]
    pagination: Dict[str, Any]


class CallSummaryResponse(BaseModel):
    """Call summary response (from Pipecat data)"""
    success: bool
    call_id: str
    summary: str
    transcript: str
    recording_url: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    patient_intent: Optional[str] = None
    esito_chiamata: Optional[str] = None
    motivazione: Optional[str] = None
    has_analysis: bool
    has_transcript: bool


class RegionItem(BaseModel):
    """Region item"""
    value: str
    label: str


class VoiceAgent(BaseModel):
    """Voice agent model"""
    id_voice_agent: int
    regione: str
    assistant_id: str


class AdditionalStatsResponse(BaseModel):
    """Additional dashboard statistics"""
    sentiment_stats: List[Dict[str, Any]]
    action_stats: List[Dict[str, Any]]
    hourly_stats: List[Dict[str, Any]]


class PatientIntentStatsResponse(BaseModel):
    """Patient intent statistics"""
    patient_intent_stats: List[Dict[str, Any]]
    total_calls_with_intent: int


class CallOutcomeStatsResponse(BaseModel):
    """Call outcome statistics"""
    outcome_stats: List[Dict[str, Any]]
    motivation_stats: List[Dict[str, Any]]
    total_calls_with_outcome: int


class MotivationAnalysisResponse(BaseModel):
    """Motivation analysis"""
    top_motivations: List[Dict[str, Any]]
    motivations_by_outcome: List[Dict[str, Any]]
    daily_trend: List[Dict[str, Any]]
    total_calls_with_motivation: int


class ClinicalKPIsResponse(BaseModel):
    """Clinical KPIs"""
    total_calls: int
    completed_calls: int
    transferred_calls: int
    not_completed_calls: int
    completion_rate: float
    transfer_rate: float
    intent_capture_rate: float
    patient_requested_transfers: int
    understanding_issues: int
    unknown_topics: int
    avg_duration_seconds: float


class TrendResponse(BaseModel):
    """Generic trend response"""
    data: List[Dict[str, Any]]
    total_entries: int


class MotivationsByOutcomeResponse(BaseModel):
    """Motivations by outcome"""
    motivations: List[Dict[str, Any]]
    total_calls: int


# ==================== Generic Response Models ====================

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool
    message: str


class ErrorResponse(BaseModel):
    """Generic error response"""
    success: bool = False
    error: str
    detail: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    agent: str
    version: str
    active_sessions: int
    services: Dict[str, str]
    database: str = "postgresql"
