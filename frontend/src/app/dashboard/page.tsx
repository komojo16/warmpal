"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { Bell, Plus, LogOut, ChevronRight, Activity, MessageSquare, Heart, Trash2, RefreshCw, Pencil } from "lucide-react";
import { format } from "date-fns";
import { ko } from "date-fns/locale";

import api from "@/lib/api";
import type { Elderly, DashboardSummary, Alert, ConversationLog } from "@/lib/api";
import EmotionChart from "@/components/EmotionChart";
import HealthTrendChart from "@/components/HealthTrendChart";
import ConversationLogView from "@/components/ConversationLog";
import RegisterElderlyModal from "@/components/RegisterElderlyModal";
import EditElderlyModal from "@/components/EditElderlyModal";

const EMOTION_KO: Record<string, string> = {
  positive: "긍정 😊", neutral: "보통 😐", negative: "부정 😔", danger: "위험 🚨",
};
const STATUS_KO: Record<string, string> = {
  normal: "정상", warning: "주의", danger: "위험",
};
const STATUS_COLOR: Record<string, string> = {
  normal: "text-green-600 bg-green-50",
  warning: "text-yellow-600 bg-yellow-50",
  danger: "text-red-600 bg-red-50",
};

export default function DashboardPage() {
  const router = useRouter();
  const [elderlyList, setElderlyList] = useState<Elderly[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [conversation, setConversation] = useState<ConversationLog | null>(null);
  const [selectedDate, setSelectedDate] = useState(format(new Date(), "yyyy-MM-dd"));
  const [showRegister, setShowRegister] = useState(false);
  const [editTarget, setEditTarget] = useState<Elderly | null>(null);
  const [showAlerts, setShowAlerts] = useState(false);
  const [activeTab, setActiveTab] = useState<"emotion" | "health" | "conversation">("emotion");
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const loadElderlyList = useCallback(async () => {
    try {
      const { data } = await api.get<Elderly[]>("/users/elderly");
      setElderlyList(data);
      if (data.length > 0 && !selectedId) setSelectedId(data[0].id);
    } catch {
      toast.error("어르신 목록을 불러오지 못했습니다.");
    }
  }, [selectedId]);

  const loadSummary = useCallback(async (id: string, silent = false) => {
    if (!silent) setLoading(true);
    try {
      const { data } = await api.get<DashboardSummary>(`/dashboard/summary/${id}`);
      setSummary(data);
    } catch {
      if (!silent) toast.error("대시보드 데이터를 불러오지 못했습니다.");
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  const loadAlerts = useCallback(async () => {
    try {
      const { data } = await api.get<Alert[]>("/dashboard/alerts", {
        params: { unread_only: false },
      });
      setAlerts(data);
    } catch {}
  }, []);

  const loadConversation = useCallback(async (elderly_id: string, date: string) => {
    try {
      const { data } = await api.get(`/dashboard/conversations/${elderly_id}`, {
        params: { date },
      });
      setConversation(data?.messages ? data : null);
    } catch {}
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) { router.push("/"); return; }
    loadElderlyList();
    loadAlerts();
  }, []);

  useEffect(() => {
    if (selectedId) {
      loadSummary(selectedId);
      loadConversation(selectedId, selectedDate);
    }
  }, [selectedId, selectedDate]);

  // 5분마다 자동 갱신
  useEffect(() => {
    if (!selectedId) return;
    const timer = setInterval(() => {
      loadSummary(selectedId, true);
      loadAlerts();
    }, 5 * 60 * 1000);
    return () => clearInterval(timer);
  }, [selectedId]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    router.push("/");
  };

  const handleReadAlert = async (id: string) => {
    await api.patch(`/dashboard/alerts/${id}/read`);
    setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, is_read: true } : a)));
  };

  const handleDeleteElderly = async (id: string, name: string) => {
    if (!confirm(`${name}을(를) 목록에서 삭제할까요?`)) return;
    try {
      await api.delete(`/users/elderly/${id}`);
      toast.success("삭제되었습니다.");
      if (selectedId === id) setSelectedId(null);
      loadElderlyList();
    } catch {
      toast.error("삭제에 실패했습니다.");
    }
  };

  const handleRefresh = async () => {
    if (!selectedId) return;
    setRefreshing(true);
    await Promise.all([loadSummary(selectedId), loadAlerts(), loadConversation(selectedId, selectedDate)]);
    setRefreshing(false);
    toast.success("새로고침 완료!");
  };

  const unreadCount = alerts.filter((a) => !a.is_read).length;

  return (
    <div className="min-h-screen bg-warm-50">
      {/* 상단 헤더 */}
      <header className="bg-white shadow-sm sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xl">🌞</span>
            <span className="font-bold text-warm-600 text-lg">따뜻한하루</span>
          </div>
          <div className="flex items-center gap-3">
            {selectedId && (
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="p-2 text-gray-500 hover:text-warm-500 disabled:opacity-40"
                title="새로고침"
              >
                <RefreshCw size={18} className={refreshing ? "animate-spin" : ""} />
              </button>
            )}
            <button onClick={() => setShowAlerts(!showAlerts)} className="relative p-2 text-gray-500 hover:text-warm-500">
              <Bell size={20} />
              {unreadCount > 0 && (
                <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-xs w-4 h-4 rounded-full flex items-center justify-center">
                  {unreadCount}
                </span>
              )}
            </button>
            <button onClick={handleLogout} className="p-2 text-gray-500 hover:text-red-500">
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </header>

      {/* 알림 드로어 */}
      {showAlerts && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/30" onClick={() => setShowAlerts(false)} />
          <div className="relative bg-white w-80 h-full overflow-y-auto shadow-xl">
            <div className="p-4 border-b font-semibold text-gray-800">알림</div>
            {alerts.length === 0 ? (
              <p className="p-4 text-sm text-gray-400 text-center">알림이 없습니다.</p>
            ) : (
              alerts.map((a) => (
                <div
                  key={a.id}
                  onClick={() => handleReadAlert(a.id)}
                  className={`p-4 border-b cursor-pointer hover:bg-gray-50 ${!a.is_read ? "bg-warm-50" : ""}`}
                >
                  <p className="text-sm text-gray-800">{a.message}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {format(new Date(a.created_at), "M월 d일 HH:mm", { locale: ko })}
                  </p>
                  {!a.is_read && <span className="badge-danger mt-1 inline-block">읽지 않음</span>}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      <main className="max-w-6xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* 사이드바: 어르신 목록 */}
          <aside className="lg:col-span-1 space-y-3">
            <div className="flex items-center justify-between mb-2">
              <h2 className="font-semibold text-gray-700">어르신 목록</h2>
              <button onClick={() => setShowRegister(true)} className="text-warm-500 hover:text-warm-600">
                <Plus size={20} />
              </button>
            </div>
            {elderlyList.length === 0 ? (
              <div className="card text-center py-8">
                <p className="text-sm text-gray-400 mb-3">등록된 어르신이 없습니다.</p>
                <button onClick={() => setShowRegister(true)} className="btn-primary text-sm">
                  어르신 등록
                </button>
              </div>
            ) : (
              elderlyList.map((e) => (
                <div
                  key={e.id}
                  onClick={() => setSelectedId(e.id)}
                  className={`card cursor-pointer transition-all ${
                    selectedId === e.id ? "ring-2 ring-warm-400 shadow-md" : "hover:shadow-md"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-800 truncate">{e.name}</p>
                      <p className="text-xs text-gray-400 mt-0.5">{e.phone}</p>
                    </div>
                    <div className="flex items-center gap-1 ml-2">
                      <button
                        onClick={(ev) => { ev.stopPropagation(); setEditTarget(e); }}
                        className="p-1 text-gray-300 hover:text-warm-400 transition-colors"
                        title="수정"
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        onClick={(ev) => { ev.stopPropagation(); handleDeleteElderly(e.id, e.name); }}
                        className="p-1 text-gray-300 hover:text-red-400 transition-colors"
                        title="삭제"
                      >
                        <Trash2 size={14} />
                      </button>
                      <ChevronRight size={16} className="text-gray-300" />
                    </div>
                  </div>
                  {e.response_streak > 0 && (
                    <p className="text-xs text-warm-500 mt-1.5 font-medium">🔥 {e.response_streak}일 연속 응답</p>
                  )}
                  {e.last_response_at && (
                    <p className="text-xs text-gray-400 mt-1">
                      마지막: {format(new Date(e.last_response_at), "M/d HH:mm")}
                    </p>
                  )}
                </div>
              ))
            )}
          </aside>

          {/* 메인 대시보드 */}
          <div className="lg:col-span-3 space-y-6">
            {!selectedId || !summary ? (
              <div className="card text-center py-20 text-gray-400">
                {loading ? "데이터를 불러오는 중..." : "어르신을 선택해 주세요."}
              </div>
            ) : (
              <>
                {/* 요약 카드 */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    {
                      icon: <Heart size={18} className="text-red-400" />,
                      label: "응답률 (7일)",
                      value: `${Math.round(summary.last_7days_response_rate * 100)}%`,
                    },
                    {
                      icon: <Activity size={18} className="text-warm-500" />,
                      label: "연속 응답",
                      value: `${summary.current_streak}일`,
                    },
                    {
                      icon: <MessageSquare size={18} className="text-indigo-400" />,
                      label: "오늘 감정",
                      value: EMOTION_KO[summary.recent_emotion.at(-1)?.emotion ?? "neutral"],
                    },
                    {
                      icon: <Bell size={18} className="text-yellow-400" />,
                      label: "읽지 않은 알림",
                      value: `${summary.unread_alerts}건`,
                    },
                  ].map((item) => (
                    <div key={item.label} className="card">
                      <div className="flex items-center gap-2 mb-2">
                        {item.icon}
                        <span className="text-xs text-gray-500">{item.label}</span>
                      </div>
                      <p className="text-xl font-bold text-gray-800">{item.value}</p>
                    </div>
                  ))}
                </div>

                {/* 탭 */}
                <div className="card">
                  <div className="flex gap-1 mb-6 bg-gray-100 rounded-lg p-1 w-fit">
                    {([
                      { key: "emotion", label: "감정 트렌드" },
                      { key: "health", label: "건강 현황" },
                      { key: "conversation", label: "대화 기록" },
                    ] as const).map(({ key, label }) => (
                      <button
                        key={key}
                        onClick={() => setActiveTab(key)}
                        className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                          activeTab === key
                            ? "bg-white text-warm-600 shadow-sm"
                            : "text-gray-500 hover:text-gray-700"
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>

                  {activeTab === "emotion" && (
                    <div>
                      <h3 className="text-sm font-semibold text-gray-700 mb-4">최근 7일 감정 변화</h3>
                      <EmotionChart data={summary.recent_emotion} />
                    </div>
                  )}

                  {activeTab === "health" && (
                    <div>
                      <h3 className="text-sm font-semibold text-gray-700 mb-2">주간 건강 현황</h3>
                      <div className="grid grid-cols-4 gap-2 mb-6">
                        {summary.health_trend.map((t) => (
                          <div key={t.date} className="text-center">
                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLOR[t.health_status]}`}>
                              {STATUS_KO[t.health_status]}
                            </span>
                            <p className="text-xs text-gray-400 mt-1">{t.date.slice(5)}</p>
                          </div>
                        ))}
                      </div>
                      <HealthTrendChart data={summary.health_trend} />
                    </div>
                  )}

                  {activeTab === "conversation" && (
                    <div>
                      <div className="flex items-center gap-3 mb-4">
                        <label className="text-sm font-medium text-gray-600">날짜</label>
                        <input
                          type="date"
                          value={selectedDate}
                          onChange={(e) => {
                            setSelectedDate(e.target.value);
                            loadConversation(selectedId!, e.target.value);
                          }}
                          max={format(new Date(), "yyyy-MM-dd")}
                          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-warm-300"
                        />
                      </div>
                      {conversation?.summary && (
                        <div className="bg-warm-50 border border-warm-200 rounded-xl px-4 py-3 mb-4">
                          <p className="text-xs font-semibold text-warm-600 mb-1">📋 AI 일일 요약</p>
                          <p className="text-sm text-gray-700">{conversation.summary}</p>
                        </div>
                      )}
                      <ConversationLogView
                        messages={conversation?.messages ?? []}
                        elderlyName={summary.elderly.name}
                      />
                    </div>
                  )}
                </div>

                {/* 빠른 리마인더 발송 */}
                <div className="card">
                  <h3 className="text-sm font-semibold text-gray-700 mb-4">리마인더 직접 발송</h3>
                  <div className="flex flex-wrap gap-2">
                    {[
                      { type: "medication", label: "💊 약 복용" },
                      { type: "meal", label: "🍚 식사" },
                      { type: "blood_pressure", label: "🩺 혈압 측정" },
                    ].map(({ type, label }) => (
                      <button
                        key={type}
                        onClick={async () => {
                          try {
                            await api.post(`/health/reminder/send/${selectedId}`, null, {
                              params: { reminder_type: type },
                            });
                            toast.success("리마인더를 발송했습니다!");
                          } catch {
                            toast.error("발송에 실패했습니다.");
                          }
                        }}
                        className="btn-secondary text-sm"
                      >
                        {label}
                      </button>
                    ))}
                    <button
                      onClick={async () => {
                        try {
                          await api.post(`/chat/hobby/${selectedId}`);
                          toast.success("취미 콘텐츠를 발송했습니다!");
                        } catch {
                          toast.error("발송에 실패했습니다.");
                        }
                      }}
                      className="btn-secondary text-sm"
                    >
                      🎮 취미 콘텐츠
                    </button>
                  </div>
                </div>

                {/* 채팅 링크 공유 */}
                <div className="card">
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">어르신 채팅 링크</h3>
                  <p className="text-xs text-gray-400 mb-3">아래 링크를 어르신 기기에 전달해 주세요.</p>
                  <div className="flex items-center gap-2">
                    <input
                      readOnly
                      value={`${typeof window !== "undefined" ? window.location.origin : ""}/chat?id=${selectedId}`}
                      className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-600 bg-gray-50 outline-none"
                    />
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(
                          `${window.location.origin}/chat?id=${selectedId}`
                        );
                        toast.success("링크를 복사했습니다!");
                      }}
                      className="btn-primary text-sm whitespace-nowrap"
                    >
                      복사
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </main>

      {showRegister && (
        <RegisterElderlyModal
          onClose={() => setShowRegister(false)}
          onSuccess={loadElderlyList}
        />
      )}

      {editTarget && (
        <EditElderlyModal
          elderly={editTarget}
          onClose={() => setEditTarget(null)}
          onSuccess={loadElderlyList}
        />
      )}
    </div>
  );
}
