// Type definitions for the application

export interface Region {
  value: string;
  label: string;
}

export interface DashboardStats {
  totalMinutes: number;
  totalRevenue: number;
  totalCalls: number;
  avgDuration: number;
}

export interface SentimentStat {
  sentiment: string;
  count: number;
  color: string;
}

export interface ActionStat {
  action: string;
  count: number;
  color: string;
}

export interface CallOutcomeStat {
  esito: string;
  count: number;
  color: string;
}

export interface ChartData {
  date: string;
  calls: number;
  minutes: number;
  revenue: number;
}

export interface Call {
  id: number;
  started_at: string;
  phone_number: string;
  call_id: string;
  interaction_id: string;
  duration_seconds: number;
  action: string;
  sentiment: string;
  esito_chiamata: string;
  motivazione: string;
}

export interface QAEntry {
  qa_id: number;
  question: string;
  answer: string;
  region: string;
  id_domanda: string;
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
  pinecone_id?: string;
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

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  functionCalled?: "RAG" | "GRAPH" | null;
}

export interface TrendData {
  date: string;
  esito_chiamata?: string;
  sentiment?: string;
  count: number;
}

export interface MotivationData {
  motivazione: string;
  count: number;
}
