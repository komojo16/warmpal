import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
});

api.interceptors.request.use((config) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("token");
      window.location.href = "/";
    }
    return Promise.reject(err);
  }
);

export default api;

// ── Types ─────────────────────────────────────────────────────────────────────

export type EmotionLabel = "positive" | "neutral" | "negative" | "danger";
export type HealthStatus = "normal" | "warning" | "danger";

export interface Elderly {
  id: string;
  name: string;
  phone: string;
  nickname: string;
  family_name: string;
  health_conditions: string[];
  medication_times: string[];
  last_response_at: string | null;
  response_streak: number;
}

export interface Message {
  role: "ai" | "elderly";
  content: string;
  timestamp: string;
  emotion: EmotionLabel | null;
  emotion_score: number | null;
}

export interface ConversationLog {
  id: string;
  elderly_id: string;
  date: string;
  messages: Message[];
  daily_emotion: EmotionLabel | null;
}

export interface DailyEmotionPoint {
  date: string;
  emotion: EmotionLabel;
  score: number;
  message_count: number;
}

export interface HealthTrendPoint {
  date: string;
  medication_rate: number;
  response_rate: number;
  health_status: HealthStatus;
}

export interface DashboardSummary {
  elderly: Elderly;
  recent_emotion: DailyEmotionPoint[];
  health_trend: HealthTrendPoint[];
  unread_alerts: number;
  last_7days_response_rate: number;
  current_streak: number;
}

export interface Alert {
  id: string;
  elderly_id: string;
  alert_type: string;
  message: string;
  created_at: string;
  is_read: boolean;
}

export interface ChatResponse {
  reply: string;
  emotion: EmotionLabel;
  timestamp: string;
}

export interface ChatHistory {
  date: string;
  messages: Message[];
  ai_display_name?: string;
  ai_avatar?: string;
}

export async function sendChatMessage(
  elderly_id: string,
  message: string
): Promise<ChatResponse> {
  const res = await api.post<ChatResponse>("/chat/message", { elderly_id, message });
  return res.data;
}

export async function getChatHistory(
  elderly_id: string,
  date?: string
): Promise<ChatHistory> {
  const params = date ? `?date=${date}` : "";
  const res = await api.get<ChatHistory>(`/chat/history/${elderly_id}${params}`);
  return res.data;
}

export interface HobbyContent {
  content: string;
  timestamp: string;
}

export async function getHobbyContent(elderly_id: string): Promise<HobbyContent> {
  const res = await api.post<HobbyContent>(`/chat/hobby/${elderly_id}`);
  return res.data;
}
