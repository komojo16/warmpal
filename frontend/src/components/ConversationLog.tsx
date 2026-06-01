"use client";
import { format } from "date-fns";
import { ko } from "date-fns/locale";
import type { Message, EmotionLabel } from "@/lib/api";

const EMOTION_BADGE: Record<EmotionLabel, string> = {
  positive: "badge-positive",
  neutral:  "badge-neutral",
  negative: "badge-negative",
  danger:   "badge-danger",
};
const EMOTION_KO: Record<EmotionLabel, string> = {
  positive: "긍정", neutral: "보통", negative: "부정", danger: "위험",
};

interface Props {
  messages: Message[];
  elderlyName: string;
}

export default function ConversationLog({ messages, elderlyName }: Props) {
  if (!messages.length) {
    return <p className="text-sm text-gray-400 text-center py-8">대화 기록이 없습니다.</p>;
  }

  return (
    <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
      {messages.map((msg, i) => {
        const isElderly = msg.role === "elderly";
        return (
          <div key={i} className={`flex ${isElderly ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] ${isElderly ? "items-end" : "items-start"} flex flex-col gap-1`}>
              <div
                className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                  isElderly
                    ? "bg-warm-500 text-white rounded-br-sm"
                    : "bg-gray-100 text-gray-800 rounded-bl-sm"
                }`}
              >
                {msg.content}
              </div>
              <div className="flex items-center gap-1.5 px-1">
                <span className="text-xs text-gray-400">
                  {format(new Date(msg.timestamp), "HH:mm", { locale: ko })}
                </span>
                {isElderly && msg.emotion && (
                  <span className={EMOTION_BADGE[msg.emotion]}>
                    {EMOTION_KO[msg.emotion]}
                  </span>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
