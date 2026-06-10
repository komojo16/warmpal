"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { format } from "date-fns";
import { ko } from "date-fns/locale";
import { sendChatMessage, getChatHistory } from "@/lib/api";
import type { Message } from "@/lib/api";
import api from "@/lib/api";

const POLL_INTERVAL_MS = 3_000; // 3초마다 새 메시지 확인

function ChatContent() {
  const searchParams = useSearchParams();
  const elderlyId = searchParams.get("id") ?? "";

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [bigFont, setBigFont] = useState(false);
  const [aiName, setAiName] = useState("warmpal");
  const [aiAvatar, setAiAvatar] = useState("💛");
  const [hasNewMessage, setHasNewMessage] = useState(false); // 새 메시지 배지
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const lastCountRef = useRef(0);
  const isAtBottomRef = useRef(true); // 스크롤이 맨 아래인지 추적

  // 스크롤 위치 감지
  const handleScroll = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const threshold = 80; // px
    isAtBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
    if (isAtBottomRef.current) setHasNewMessage(false);
  }, []);

  const scrollToBottom = useCallback((force = false) => {
    if (force || isAtBottomRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
      setHasNewMessage(false);
    }
  }, []);

  const loadHistory = useCallback(async (silent = false) => {
    if (!elderlyId) return;
    try {
      const res = await getChatHistory(elderlyId);
      if (res.ai_display_name) setAiName(res.ai_display_name);
      if (res.ai_avatar) setAiAvatar(res.ai_avatar);

      const newCount = res.messages.length;
      const hasNew = newCount > lastCountRef.current;
      lastCountRef.current = newCount;
      setMessages(res.messages);

      // 새 메시지가 왔고 사용자가 위로 스크롤 중이면 배지만 표시
      if (hasNew && !isAtBottomRef.current) {
        setHasNewMessage(true);
      }
    } catch {
      // 네트워크 오류는 조용히 무시
    } finally {
      if (!silent) setInitializing(false);
    }
  }, [elderlyId]);

  // 초기 로드
  useEffect(() => {
    if (!elderlyId) { setInitializing(false); return; }
    loadHistory(false);
  }, [elderlyId, loadHistory]);

  // 3초마다 폴링 (스케줄러 메시지 수신)
  useEffect(() => {
    if (!elderlyId) return;
    const timer = setInterval(() => loadHistory(true), POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [elderlyId, loadHistory]);

  // 새 메시지 → 맨 아래에 있을 때만 자동 스크롤
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  async function handleSend(overrideText?: string) {
    const text = (overrideText ?? input).trim();
    if (!text || loading || !elderlyId) return;

    const userMsg: Message = {
      role: "elderly",
      content: text,
      timestamp: new Date().toISOString(),
      emotion: null,
      emotion_score: null,
    };
    setMessages((prev) => [...prev, userMsg]);
    lastCountRef.current += 1;
    setInput("");
    setLoading(true);
    isAtBottomRef.current = true; // 내가 보낸 메시지는 항상 아래로

    try {
      const res = await sendChatMessage(elderlyId, text);
      const aiMsg: Message = {
        role: "ai",
        content: res.reply,
        timestamp: res.timestamp,
        emotion: null,
        emotion_score: null,
      };
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = { ...userMsg, emotion: res.emotion as Message["emotion"] };
        return [...updated, aiMsg];
      });
      lastCountRef.current += 1;
      scrollToBottom(true);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          content: "죄송해요, 잠시 문제가 생겼어요. 조금 뒤에 다시 말씀해 주세요.",
          timestamp: new Date().toISOString(),
          emotion: null,
          emotion_score: null,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handleHobby(contentType: "song" | "quiz") {
    if (loading || !elderlyId) return;
    setLoading(true);
    try {
      const { data } = await api.post<{ content: string; timestamp: string }>(
        `/chat/hobby/${elderlyId}?content_type=${contentType}`
      );
      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          content: data.content,
          timestamp: data.timestamp,
          emotion: null,
          emotion_score: null,
        },
      ]);
    } catch {
      // 조용히 무시
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const msgClass = bigFont
    ? "text-xl leading-relaxed"
    : "text-sm leading-relaxed";

  const timeClass = bigFont ? "text-sm text-white/70 px-1" : "text-[11px] text-white/70 px-1";

  if (!elderlyId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-warm-50">
        <p className="text-gray-500 text-lg">잘못된 접근입니다. 가족에게 올바른 링크를 받으세요.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-[#b2c7d9]">
      {/* 헤더 */}
      <header className="bg-[#4a90b8] text-white px-4 py-3 flex items-center gap-3 shadow">
        <div className="w-9 h-9 rounded-full bg-warm-400 flex-shrink-0 flex items-center justify-center text-lg">
          {aiAvatar}
        </div>
        <div className="flex-1">
          <p className="font-semibold text-sm">{aiName}</p>
          <p className="text-xs text-blue-100">AI 케어 서비스</p>
        </div>
        {/* 글씨 크기 토글 */}
        <button
          onClick={() => setBigFont((v) => !v)}
          className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
            bigFont ? "bg-white text-[#4a90b8]" : "bg-[#3a7aa8] text-white"
          }`}
          title="글씨 크기 변경"
        >
          {bigFont ? "글씨 작게" : "글씨 크게"}
        </button>
      </header>

      {/* 날짜 구분 */}
      <div className="flex justify-center py-2">
        <span className="bg-[#9ab3c4] text-white text-xs px-3 py-1 rounded-full">
          {format(new Date(), "yyyy년 M월 d일 EEEE", { locale: ko })}
        </span>
      </div>

      {/* 메시지 목록 */}
      {/* 새 메시지 배지 */}
      {hasNewMessage && (
        <div className="flex justify-center py-1">
          <button
            onClick={() => scrollToBottom(true)}
            className="bg-[#4a90b8] text-white text-xs px-4 py-1.5 rounded-full shadow-md animate-bounce"
          >
            새 메시지 ↓
          </button>
        </div>
      )}

      <main
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-3 py-2 space-y-2"
      >
        {initializing && (
          <div className="flex justify-center py-8">
            <span className="text-white text-sm">대화를 불러오는 중...</span>
          </div>
        )}

        {!initializing && messages.length === 0 && (
          <div className="flex justify-center py-8">
            <span className="bg-[#9ab3c4] text-white text-xs px-3 py-1 rounded-full">
              오늘 첫 대화예요. 안녕하세요! 👋
            </span>
          </div>
        )}

        {messages.map((msg, i) => {
          const isElderly = msg.role === "elderly";
          return (
            <div key={i} className={`flex items-end gap-2 ${isElderly ? "flex-row-reverse" : "flex-row"}`}>
              {!isElderly && (
                <div className="w-9 h-9 rounded-full bg-warm-400 flex-shrink-0 flex items-center justify-center text-lg mb-1">
                  {aiAvatar}
                </div>
              )}

              <div className={`flex flex-col gap-0.5 max-w-[72%] ${isElderly ? "items-end" : "items-start"}`}>
                {!isElderly && (
                  <span className={`${bigFont ? "text-sm" : "text-xs"} text-white ml-1`}>{aiName}</span>
                )}

                <div
                  className={`px-4 py-2.5 rounded-2xl whitespace-pre-wrap break-words ${msgClass} ${
                    isElderly
                      ? "bg-[#fee500] text-gray-900 rounded-br-sm"
                      : "bg-white text-gray-900 rounded-bl-sm shadow-sm"
                  }`}
                >
                  {msg.content}
                </div>

                <span className={timeClass}>
                  {format(new Date(msg.timestamp), "a h:mm", { locale: ko })}
                </span>
              </div>
            </div>
          );
        })}

        {/* AI 응답 대기 중 */}
        {loading && (
          <div className="flex items-end gap-2">
            <div className="w-9 h-9 rounded-full bg-warm-400 flex-shrink-0 flex items-center justify-center text-lg">
              {aiAvatar}
            </div>
            <div className="flex flex-col gap-0.5 items-start">
              <span className="text-xs text-white ml-1">{aiName}</span>
              <div className="bg-white rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
                <span className="flex gap-1">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
                </span>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      {/* 빠른 입력 버튼 */}
      <div className="bg-[#9ab3c4] px-3 pt-2 pb-0 flex gap-2 overflow-x-auto">
        {[
          { label: "🎵 노래 추천", hobbyType: "song" as const },
          { label: "🧩 퀴즈 내줘", hobbyType: "quiz" as const },
        ].map((item) => (
          <button
            key={item.label}
            onClick={() => item.hobbyType ? handleHobby(item.hobbyType) : handleSend(item.msg)}
            disabled={loading}
            className="flex-shrink-0 bg-white text-gray-700 text-xs px-3 py-1.5 rounded-full mb-2 disabled:opacity-40"
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* 입력창 */}
      <footer className="bg-[#9ab3c4] px-3 py-2 flex items-end gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          placeholder="메시지를 입력하세요..."
          className={`flex-1 resize-none bg-white rounded-2xl px-4 py-2.5 text-gray-900 placeholder-gray-400 outline-none max-h-32 overflow-y-auto ${bigFont ? "text-lg" : "text-sm"}`}
          style={{ lineHeight: "1.5" }}
          disabled={loading}
        />
        <button
          onClick={() => handleSend()}
          disabled={loading || !input.trim()}
          className="w-10 h-10 rounded-full bg-[#fee500] flex items-center justify-center flex-shrink-0 disabled:opacity-40 transition-opacity"
          aria-label="전송"
        >
          <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5">
            <path d="M5 12h14M13 6l6 6-6 6" stroke="#1a1a1a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </footer>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-[#b2c7d9]">
        <span className="text-white">불러오는 중...</span>
      </div>
    }>
      <ChatContent />
    </Suspense>
  );
}
