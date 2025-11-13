// Dummy data for all pages - to be replaced with real API calls later

export const dummyRegions = [
  { value: "All Region", label: "All Region" },
  { value: "Piemonte", label: "Piemonte" },
  { value: "Lombardia", label: "Lombardia" },
  { value: "Veneto", label: "Veneto" },
];

export const dummyDashboardStats = {
  totalMinutes: 45280,
  totalRevenue: 271.68,
  totalCalls: 1842,
  avgDuration: 24.6,
};

export const dummySentimentStats = [
  { sentiment: "Positive", count: 892, color: "#28a745" },
  { sentiment: "Neutral", count: 654, color: "#007bff" },
  { sentiment: "Negative", count: 296, color: "#dc3545" },
];

export const dummyActionStats = [
  { action: "Completed", count: 1124, color: "#007bff" },
  { action: "Transfer", count: 486, color: "#ffc107" },
  { action: "Book", count: 152, color: "#28a745" },
  { action: "Question", count: 58, color: "#17a2b8" },
  { action: "Time Limit", count: 22, color: "#dc3545" },
];

export const dummyCallOutcomeStats = [
  { esito: "COMPLETATA", count: 1124, color: "#28a745" },
  { esito: "TRASFERITA", count: 486, color: "#ffc107" },
  { esito: "NON COMPLETATA", count: 232, color: "#dc3545" },
];

export const dummyChartData = [
  { date: "2024-01-08", calls: 245, minutes: 5890, revenue: 35.34 },
  { date: "2024-01-09", calls: 268, minutes: 6420, revenue: 38.52 },
  { date: "2024-01-10", calls: 289, minutes: 6936, revenue: 41.62 },
  { date: "2024-01-11", calls: 256, minutes: 6144, revenue: 36.86 },
  { date: "2024-01-12", calls: 278, minutes: 6672, revenue: 40.03 },
  { date: "2024-01-13", calls: 302, minutes: 7248, revenue: 43.49 },
  { date: "2024-01-14", calls: 204, minutes: 4896, revenue: 29.38 },
];

export const dummyRecentCalls = Array.from({ length: 100 }, (_, i) => ({
  id: i + 1,
  started_at: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toISOString(),
  phone_number: `+39 ${Math.floor(Math.random() * 9000000000 + 1000000000)}`,
  call_id: `call_${Math.random().toString(36).substr(2, 9)}`,
  interaction_id: `int_${Math.random().toString(36).substr(2, 9)}`,
  duration_seconds: Math.floor(Math.random() * 600 + 60),
  action: ["transfer", "book", "question", "completed_by_voice_agent", "time_limit"][Math.floor(Math.random() * 5)],
  sentiment: ["positive", "negative", "neutral"][Math.floor(Math.random() * 3)],
  esito_chiamata: ["COMPLETATA", "TRASFERITA", "NON COMPLETATA"][Math.floor(Math.random() * 3)],
  motivazione: ["Info fornite", "Mancata comprensione", "Argomento sconosciuto", "Richiesta paziente", "Interrotta dal paziente"][Math.floor(Math.random() * 5)],
}));

export const dummyQAEntries = [
  {
    qa_id: 1,
    question: "Come posso prenotare una visita specialistica?",
    answer: "Per prenotare una visita specialistica, può chiamare il numero verde 800-123456 dal lunedì al venerdì dalle 8:00 alle 18:00, oppure utilizzare il portale online accessibile dal nostro sito web.",
    region: "Piemonte",
    id_domanda: "N0001",
    created_at: "2024-01-15T10:30:00",
    updated_at: "2024-01-15T10:30:00",
    created_by: "Mario Rossi",
    updated_by: "Mario Rossi",
  },
  {
    qa_id: 2,
    question: "Quali documenti servono per la prima visita?",
    answer: "Per la prima visita sono necessari: documento di identità valido, tessera sanitaria, impegnativa del medico curante e eventuali esami precedenti relativi alla problematica.",
    region: "Piemonte",
    id_domanda: "N0002",
    created_at: "2024-01-14T14:20:00",
    updated_at: "2024-01-16T09:15:00",
    created_by: "Laura Bianchi",
    updated_by: "Mario Rossi",
  },
  {
    qa_id: 3,
    question: "È possibile cancellare una prenotazione?",
    answer: "Sì, è possibile cancellare una prenotazione chiamando il numero verde almeno 48 ore prima dell'appuntamento o tramite il portale online accedendo alla sezione 'Le mie prenotazioni'.",
    region: "Lombardia",
    id_domanda: "N0003",
    created_at: "2024-01-13T11:45:00",
    updated_at: "2024-01-13T11:45:00",
    created_by: "Giuseppe Verdi",
    updated_by: "Giuseppe Verdi",
  },
  {
    qa_id: 4,
    question: "Quanto tempo prima devo arrivare per la visita?",
    answer: "Si consiglia di arrivare almeno 15 minuti prima dell'orario dell'appuntamento per completare le eventuali pratiche amministrative.",
    region: "Piemonte",
    id_domanda: "N0004",
    created_at: "2024-01-12T16:00:00",
    updated_at: "2024-01-12T16:00:00",
    created_by: "Laura Bianchi",
    updated_by: "Laura Bianchi",
  },
  {
    qa_id: 5,
    question: "Come posso ottenere il referto della visita?",
    answer: "Il referto sarà disponibile nell'area riservata del portale online entro 7 giorni lavorativi dalla visita. Riceverà anche una notifica via email quando il referto sarà pronto.",
    region: "Veneto",
    id_domanda: "N0005",
    created_at: "2024-01-11T09:30:00",
    updated_at: "2024-01-17T10:20:00",
    created_by: "Anna Ferrari",
    updated_by: "Mario Rossi",
  },
];

export const dummyUsers = [
  {
    user_id: 1,
    email: "mario.rossi@voila.com",
    nome: "Mario",
    cognome: "Rossi",
    ruolo: "master",
    region: "master",
    is_active: true,
    created_at: "2024-01-10T08:00:00",
    updated_at: "2024-01-10T08:00:00",
  },
  {
    user_id: 2,
    email: "laura.bianchi@voila.com",
    nome: "Laura",
    cognome: "Bianchi",
    ruolo: "Piemonte",
    region: "Piemonte",
    is_active: true,
    created_at: "2024-01-11T09:15:00",
    updated_at: "2024-01-11T09:15:00",
  },
  {
    user_id: 3,
    email: "giuseppe.verdi@voila.com",
    nome: "Giuseppe",
    cognome: "Verdi",
    ruolo: "Lombardia",
    region: "Lombardia",
    is_active: false,
    created_at: "2024-01-12T10:30:00",
    updated_at: "2024-01-15T14:20:00",
  },
  {
    user_id: 4,
    email: "anna.ferrari@voila.com",
    nome: "Anna",
    cognome: "Ferrari",
    ruolo: "Veneto",
    region: "Veneto",
    is_active: true,
    created_at: "2024-01-13T11:45:00",
    updated_at: "2024-01-13T11:45:00",
  },
];

export const dummyChatMessages = [
  {
    id: "1",
    role: "user",
    content: "Vorrei prenotare una visita cardiologica",
    timestamp: new Date(Date.now() - 5 * 60 * 1000),
  },
  {
    id: "2",
    role: "assistant",
    content: "Certamente! Per prenotare una visita cardiologica ho bisogno di alcune informazioni. Ha già l'impegnativa del medico di base?",
    timestamp: new Date(Date.now() - 4.5 * 60 * 1000),
    functionCalled: "RAG",
  },
  {
    id: "3",
    role: "user",
    content: "Sì, ce l'ho",
    timestamp: new Date(Date.now() - 3 * 60 * 1000),
  },
  {
    id: "4",
    role: "assistant",
    content: "Perfetto! Abbiamo disponibilità per il 25 gennaio alle ore 14:30 oppure il 28 gennaio alle ore 10:00. Quale preferisce?",
    timestamp: new Date(Date.now() - 2.5 * 60 * 1000),
    functionCalled: "GRAPH",
  },
];

export const dummyOutcomeTrend = [
  { date: "2024-01-08", esito_chiamata: "COMPLETATA", count: 156 },
  { date: "2024-01-08", esito_chiamata: "TRASFERITA", count: 68 },
  { date: "2024-01-08", esito_chiamata: "NON COMPLETATA", count: 21 },
  { date: "2024-01-09", esito_chiamata: "COMPLETATA", count: 172 },
  { date: "2024-01-09", esito_chiamata: "TRASFERITA", count: 72 },
  { date: "2024-01-09", esito_chiamata: "NON COMPLETATA", count: 24 },
  { date: "2024-01-10", esito_chiamata: "COMPLETATA", count: 185 },
  { date: "2024-01-10", esito_chiamata: "TRASFERITA", count: 78 },
  { date: "2024-01-10", esito_chiamata: "NON COMPLETATA", count: 26 },
  { date: "2024-01-11", esito_chiamata: "COMPLETATA", count: 164 },
  { date: "2024-01-11", esito_chiamata: "TRASFERITA", count: 70 },
  { date: "2024-01-11", esito_chiamata: "NON COMPLETATA", count: 22 },
  { date: "2024-01-12", esito_chiamata: "COMPLETATA", count: 178 },
  { date: "2024-01-12", esito_chiamata: "TRASFERITA", count: 75 },
  { date: "2024-01-12", esito_chiamata: "NON COMPLETATA", count: 25 },
  { date: "2024-01-13", esito_chiamata: "COMPLETATA", count: 193 },
  { date: "2024-01-13", esito_chiamata: "TRASFERITA", count: 82 },
  { date: "2024-01-13", esito_chiamata: "NON COMPLETATA", count: 27 },
  { date: "2024-01-14", esito_chiamata: "COMPLETATA", count: 131 },
  { date: "2024-01-14", esito_chiamata: "TRASFERITA", count: 56 },
  { date: "2024-01-14", esito_chiamata: "NON COMPLETATA", count: 17 },
];

export const dummySentimentTrend = [
  { date: "2024-01-08", sentiment: "positive", count: 128 },
  { date: "2024-01-08", sentiment: "neutral", count: 94 },
  { date: "2024-01-08", sentiment: "negative", count: 23 },
  { date: "2024-01-09", sentiment: "positive", count: 140 },
  { date: "2024-01-09", sentiment: "neutral", count: 102 },
  { date: "2024-01-09", sentiment: "negative", count: 26 },
  { date: "2024-01-10", sentiment: "positive", count: 151 },
  { date: "2024-01-10", sentiment: "neutral", count: 110 },
  { date: "2024-01-10", sentiment: "negative", count: 28 },
  { date: "2024-01-11", sentiment: "positive", count: 134 },
  { date: "2024-01-11", sentiment: "neutral", count: 98 },
  { date: "2024-01-11", sentiment: "negative", count: 24 },
  { date: "2024-01-12", sentiment: "positive", count: 145 },
  { date: "2024-01-12", sentiment: "neutral", count: 106 },
  { date: "2024-01-12", sentiment: "negative", count: 27 },
  { date: "2024-01-13", sentiment: "positive", count: 158 },
  { date: "2024-01-13", sentiment: "neutral", count: 115 },
  { date: "2024-01-13", sentiment: "negative", count: 29 },
  { date: "2024-01-14", sentiment: "positive", count: 107 },
  { date: "2024-01-14", sentiment: "neutral", count: 78 },
  { date: "2024-01-14", sentiment: "negative", count: 19 },
];

export const dummyCompletedMotivations = [
  { motivazione: "Info fornite", count: 1124 },
];

export const dummyTransferredMotivations = [
  { motivazione: "Mancata comprensione", count: 186 },
  { motivazione: "Argomento sconosciuto", count: 152 },
  { motivazione: "Richiesta paziente", count: 148 },
];

export const dummyNotCompletedMotivations = [
  { motivazione: "Interrotta dal paziente", count: 232 },
];
