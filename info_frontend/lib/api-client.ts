/**
 * API Client for Dashboard Backend
 * Handles all API requests to the FastAPI backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8081/api";

// ==================== Types ====================

export interface LoginRequest {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface LoginResponse {
  success: boolean;
  message: string;
  access_token: string;
  token_type: string;
  user: {
    user_id: number;
    email: string;
    name: string;
    role: string;
    region: string;
  };
}

export interface User {
  user_id: number;
  email: string;
  nome: string;
  cognome: string;
  ruolo: string;
  region: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface QAItem {
  qa_id: number;
  question: string;
  answer: string;
  region: string;
  pinecone_id?: string;
  created_at?: string;
  updated_at?: string;
  created_by?: string;
  updated_by?: string;
  id_domanda?: string;
}

export interface DashboardStats {
  total_minutes: number;
  total_revenue: number;
  total_calls: number;
  chart_data: Array<{
    date: string;
    calls: number;
    minutes: number;
    revenue: number;
  }>;
  avg_duration_minutes: number;
}

export interface Region {
  value: string;
  label: string;
}

export interface CallItem {
  id: number;
  started_at: string | null;
  call_id: string | null;
  interaction_id: string | null;
  phone_number: string | null;
  duration_seconds: number;
  action: string;
  sentiment: string;
  motivazione: string | null;
  esito_chiamata: string | null;
}

export interface CallListResponse {
  calls: CallItem[];
  pagination: {
    total_calls: number;
    total_pages: number;
    current_page: number;
    has_next: boolean;
    has_previous: boolean;
    limit: number;
    offset: number;
  };
}

export interface CallSummaryResponse {
  success: boolean;
  call_id: string;
  summary: string;
  transcript: string;
  recording_url?: string;
  started_at?: string;
  ended_at?: string;
  patient_intent?: string;
  esito_chiamata?: string;
  motivazione?: string;
  has_analysis: boolean;
  has_transcript: boolean;
}

export interface VoiceAgent {
  id_voice_agent: number;
  regione: string;
  assistant_id: string;
}

export interface CreateUserResponse {
  success: boolean;
  message: string;
  user_id: number;
  email_sent: boolean;
}

export interface ToggleStatusResponse {
  success: boolean;
  message: string;
  new_status: boolean;
}

export interface ResendCredentialsResponse {
  success: boolean;
  message: string;
  email_sent: boolean;
}

export interface DeleteResponse {
  success: boolean;
  message: string;
}

export interface QACreateResponse {
  success: boolean;
  message: string;
  qa_id: number;
  pinecone_id: string;
  id_domanda: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  timezone: string;
}

export interface QAUpdateResponse {
  success: boolean;
  message: string;
  qa_id: number;
  old_pinecone_id: string;
  new_pinecone_id: string;
  updated_by: string;
  updated_at: string;
  updated_at_timezone: string;
}

export interface QADeleteResponse {
  success: boolean;
  message: string;
  qa_id: number;
  pinecone_id?: string;
}

export interface QAStatsResponse {
  region: string;
  total_qa: number;
  recent_qa: number;
  updated_qa: number;
}

export interface AdditionalStats {
  sentiment_stats: Array<{ sentiment: string; count: number }>;
  action_stats: Array<{ action: string; count: number; avg_duration: number }>;
  hourly_stats: Array<{ hour: number; calls_count: number }>;
}

export interface ClinicalKPIs {
  total_calls: number;
  completed_calls: number;
  transferred_calls: number;
  not_completed_calls: number;
  completion_rate: number;
  transfer_rate: number;
  intent_capture_rate: number;
  patient_requested_transfers: number;
  understanding_issues: number;
  unknown_topics: number;
  avg_duration_seconds: number;
}

export interface TrendDataPoint {
  date: string;
  count: number;
  esito_chiamata?: string;
  sentiment?: string;
}

export interface TrendResponse {
  data: TrendDataPoint[];
  total_entries: number;
}

export interface CallOutcomeStats {
  outcome_stats: Array<{ esito_chiamata: string; count: number }>;
  motivation_stats: Array<{ motivazione: string; count: number }>;
  total_calls_with_outcome: number;
}

// ==================== Helper Functions ====================

function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('auth_token');
}

function getAuthHeaders(): HeadersInit {
  const token = getAuthToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return headers;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || error.message || `HTTP ${response.status}`);
  }
  return response.json();
}

// ==================== Authentication ====================

export const authApi = {
  async login(data: LoginRequest): Promise<LoginResponse> {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    
    const result = await handleResponse<LoginResponse>(response);
    
    // Store token in localStorage
    if (result.access_token) {
      localStorage.setItem('auth_token', result.access_token);
      localStorage.setItem('user', JSON.stringify(result.user));
    }
    
    return result;
  },

  async verify(): Promise<{ valid: boolean; user: LoginResponse['user'] }> {
    const response = await fetch(`${API_BASE_URL}/auth/verify`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async logout(): Promise<void> {
    await fetch(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    
    // Clear local storage
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
  },
};

// ==================== Users ====================

export const usersApi = {
  async list(): Promise<User[]> {
    const response = await fetch(`${API_BASE_URL}/users`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async create(data: { nome: string; cognome: string; email: string; ruolo: string }): Promise<CreateUserResponse> {
    const response = await fetch(`${API_BASE_URL}/users`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  async toggleStatus(userId: number): Promise<ToggleStatusResponse> {
    const response = await fetch(`${API_BASE_URL}/users/${userId}/toggle-status`, {
      method: 'PUT',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async resendCredentials(userId: number): Promise<ResendCredentialsResponse> {
    const response = await fetch(`${API_BASE_URL}/users/${userId}/resend-credentials`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async delete(userId: number): Promise<DeleteResponse> {
    const response = await fetch(`${API_BASE_URL}/users/${userId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },
};

// ==================== Q&A ====================

export const qaApi = {
  async listByRegion(region: string): Promise<QAItem[]> {
    const response = await fetch(`${API_BASE_URL}/qa/region/${encodeURIComponent(region)}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async create(data: { question: string; answer: string; region: string }): Promise<QACreateResponse> {
    const response = await fetch(`${API_BASE_URL}/qa`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  async update(qaId: number, data: { question: string; answer: string }): Promise<QAUpdateResponse> {
    const response = await fetch(`${API_BASE_URL}/qa/${qaId}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  },

  async delete(qaId: number): Promise<QADeleteResponse> {
    const response = await fetch(`${API_BASE_URL}/qa/${qaId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async getStats(region: string): Promise<QAStatsResponse> {
    const response = await fetch(`${API_BASE_URL}/qa/stats/${encodeURIComponent(region)}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },
};

// ==================== Dashboard ====================

export const dashboardApi = {
  async getStats(params?: { region?: string; start_date?: string; end_date?: string }): Promise<DashboardStats> {
    const queryParams = new URLSearchParams();
    if (params?.region) queryParams.append('region', params.region);
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);
    
    const url = `${API_BASE_URL}/dashboard/stats${queryParams.toString() ? `?${queryParams}` : ''}`;
    const response = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async getCalls(params?: { limit?: number; offset?: number; region?: string; start_date?: string; end_date?: string }): Promise<CallListResponse> {
    const queryParams = new URLSearchParams();
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.offset) queryParams.append('offset', params.offset.toString());
    if (params?.region) queryParams.append('region', params.region);
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);
    
    const url = `${API_BASE_URL}/dashboard/calls${queryParams.toString() ? `?${queryParams}` : ''}`;
    const response = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async getCallSummary(callId: string): Promise<CallSummaryResponse> {
    const response = await fetch(`${API_BASE_URL}/dashboard/call/${callId}/summary`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async getRegions(): Promise<Region[]> {
    const response = await fetch(`${API_BASE_URL}/dashboard/regions`);
    return handleResponse(response);
  },

  async getVoiceAgents(): Promise<VoiceAgent[]> {
    const response = await fetch(`${API_BASE_URL}/dashboard/voice-agents`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async getAdditionalStats(params?: { region?: string; start_date?: string; end_date?: string }): Promise<AdditionalStats> {
    const queryParams = new URLSearchParams();
    if (params?.region) queryParams.append('region', params.region);
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);
    
    const url = `${API_BASE_URL}/dashboard/additional-stats${queryParams.toString() ? `?${queryParams}` : ''}`;
    const response = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async getClinicalKPIs(params?: { region?: string; start_date?: string; end_date?: string }): Promise<ClinicalKPIs> {
    const queryParams = new URLSearchParams();
    if (params?.region) queryParams.append('region', params.region);
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);

    const url = `${API_BASE_URL}/dashboard/clinical-kpis${queryParams.toString() ? `?${queryParams}` : ''}`;
    const response = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async getCallOutcomeTrend(params?: { region?: string; start_date?: string; end_date?: string }): Promise<TrendResponse> {
    const queryParams = new URLSearchParams();
    if (params?.region) queryParams.append('region', params.region);
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);

    const url = `${API_BASE_URL}/dashboard/call-outcome-trend${queryParams.toString() ? `?${queryParams}` : ''}`;
    const response = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async getSentimentTrend(params?: { region?: string; start_date?: string; end_date?: string }): Promise<TrendResponse> {
    const queryParams = new URLSearchParams();
    if (params?.region) queryParams.append('region', params.region);
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);

    const url = `${API_BASE_URL}/dashboard/sentiment-trend${queryParams.toString() ? `?${queryParams}` : ''}`;
    const response = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },

  async getCallOutcomeStats(params?: { region?: string; start_date?: string; end_date?: string }): Promise<CallOutcomeStats> {
    const queryParams = new URLSearchParams();
    if (params?.region) queryParams.append('region', params.region);
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);

    const url = `${API_BASE_URL}/dashboard/call-outcome-stats${queryParams.toString() ? `?${queryParams}` : ''}`;
    const response = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse(response);
  },
};

// ==================== Utilities ====================

export function isAuthenticated(): boolean {
  return !!getAuthToken();
}

export function getCurrentUser(): LoginResponse['user'] | null {
  if (typeof window === 'undefined') return null;
  const userStr = localStorage.getItem('user');
  return userStr ? JSON.parse(userStr) : null;
}
