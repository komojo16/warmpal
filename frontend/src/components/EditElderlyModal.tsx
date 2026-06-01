"use client";

import { useState } from "react";
import { X, Plus, Trash2 } from "lucide-react";
import toast from "react-hot-toast";
import api from "@/lib/api";
import type { Elderly } from "@/lib/api";

interface Props {
  elderly: Elderly;
  onClose: () => void;
  onSuccess: () => void;
}

export default function EditElderlyModal({ elderly, onClose, onSuccess }: Props) {
  const PERSONAS = ["케어 도우미", "손자", "손녀", "아들", "딸", "친구"];

  const [nickname, setNickname] = useState(elderly.nickname ?? "어르신");
  const [aiPersona, setAiPersona] = useState((elderly as any).ai_persona ?? "케어 도우미");
  const [gender, setGender] = useState((elderly as any).gender ?? "여성");
  const [aiDisplayName, setAiDisplayName] = useState((elderly as any).ai_display_name ?? "따뜻한하루");
  const [aiAvatar, setAiAvatar] = useState((elderly as any).ai_avatar ?? "💛");
  const [friendName, setFriendName] = useState((elderly as any).friend_name ?? "");
  const [proactiveEnabled, setProactiveEnabled] = useState((elderly as any).proactive_enabled ?? true);
  const [proactiveStart, setProactiveStart] = useState((elderly as any).proactive_start_hour ?? 10);
  const [proactiveEnd, setProactiveEnd] = useState((elderly as any).proactive_end_hour ?? 20);
  const [proactiveTimes, setProactiveTimes] = useState((elderly as any).proactive_times_per_day ?? 2);

  const AVATARS = ["💛", "🌸", "🌟", "😊", "🤗", "👴", "👵", "🌿", "🍀", "☀️", "🌈", "💙"];
  const [medTimes, setMedTimes] = useState<string[]>(
    elderly.medication_times?.length ? [...elderly.medication_times] : ["08:00"]
  );
  const [conditions, setConditions] = useState<string[]>(
    elderly.health_conditions?.length ? [...elderly.health_conditions] : []
  );
  const [condInput, setCondInput] = useState("");
  const [saving, setSaving] = useState(false);

  const addMedTime = () => {
    if (medTimes.length >= 6) return;
    setMedTimes((prev) => [...prev, "09:00"]);
  };

  const removeMedTime = (i: number) => {
    setMedTimes((prev) => prev.filter((_, idx) => idx !== i));
  };

  const updateMedTime = (i: number, val: string) => {
    setMedTimes((prev) => prev.map((t, idx) => (idx === i ? val : t)));
  };

  const addCondition = () => {
    const v = condInput.trim();
    if (!v || conditions.includes(v)) return;
    setConditions((prev) => [...prev, v]);
    setCondInput("");
  };

  const removeCondition = (v: string) => {
    setConditions((prev) => prev.filter((c) => c !== v));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.patch(`/users/elderly/${elderly.id}`, {
        nickname: nickname.trim() || "어르신",
        medication_times: medTimes.filter(Boolean).sort(),
        health_conditions: conditions,
        ai_persona: aiPersona,
        gender,
        ai_display_name: aiDisplayName.trim() || "따뜻한하루",
        ai_avatar: aiAvatar,
        friend_name: friendName.trim(),
        proactive_enabled: proactiveEnabled,
        proactive_start_hour: proactiveStart,
        proactive_end_hour: proactiveEnd,
        proactive_times_per_day: proactiveTimes,
      });
      toast.success("저장되었습니다.");
      onSuccess();
      onClose();
    } catch {
      toast.error("저장에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
        {/* 헤더 */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="font-semibold text-gray-800">{elderly.name} 설정</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <div className="px-6 py-5 space-y-6">
          {/* 채팅 프로필 설정 */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">💬 채팅창 프로필</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-500 mb-1 block">AI 이름 (채팅창에 표시)</label>
                <input
                  type="text"
                  value={aiDisplayName}
                  onChange={(e) => setAiDisplayName(e.target.value)}
                  placeholder="따뜻한하루"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-warm-300"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-2 block">프로필 이모지</label>
                <div className="flex flex-wrap gap-2">
                  {AVATARS.map((e) => (
                    <button
                      key={e}
                      onClick={() => setAiAvatar(e)}
                      className={`w-10 h-10 rounded-full text-xl flex items-center justify-center border-2 transition-colors ${
                        aiAvatar === e ? "border-warm-400 bg-warm-50" : "border-transparent hover:border-gray-200"
                      }`}
                    >
                      {e}
                    </button>
                  ))}
                </div>
              </div>
              {/* 미리보기 */}
              <div className="flex items-center gap-3 bg-[#b2c7d9] rounded-xl px-4 py-3">
                <div className="w-9 h-9 rounded-full bg-warm-400 flex items-center justify-center text-lg flex-shrink-0">
                  {aiAvatar}
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">{aiDisplayName || "따뜻한하루"}</p>
                  <p className="text-xs text-white/70">AI 케어 서비스</p>
                </div>
              </div>
            </div>
          </section>

          {/* AI 역할 설정 */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">🤖 AI 역할</h3>
            <p className="text-xs text-gray-400 mb-2">어르신과 대화할 때 AI가 맡을 역할을 선택하세요.</p>
            <div className="flex flex-wrap gap-2">
              {PERSONAS.map((p) => (
                <button
                  key={p}
                  onClick={() => setAiPersona(p)}
                  className={`px-4 py-2 rounded-full text-sm font-medium border transition-colors ${
                    aiPersona === p
                      ? "bg-warm-500 text-white border-warm-500"
                      : "bg-white text-gray-600 border-gray-200 hover:border-warm-300"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
            {/* 성별 선택 */}
            <div className="mt-4">
              <p className="text-xs text-gray-500 mb-2">어르신 성별 <span className="text-gray-400">(호칭 자동 결정에 사용)</span></p>
              <div className="flex gap-2">
                {["여성", "남성"].map((g) => (
                  <button
                    key={g}
                    onClick={() => setGender(g)}
                    className={`flex-1 py-2 rounded-lg text-sm font-medium border transition-colors ${
                      gender === g
                        ? "bg-warm-500 text-white border-warm-500"
                        : "bg-white text-gray-600 border-gray-200 hover:border-warm-300"
                    }`}
                  >
                    {g === "여성" ? "👩 여성" : "👨 남성"}
                  </button>
                ))}
              </div>
            </div>

            {/* 페르소나별 호칭 입력 */}
            <div className="mt-3">
              {aiPersona === "케어 도우미" && (
                <>
                  <label className="text-xs text-gray-500 mb-1 block">AI가 어르신을 부를 호칭</label>
                  <input
                    type="text"
                    value={nickname}
                    onChange={(e) => setNickname(e.target.value)}
                    placeholder="어르신"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-warm-300"
                  />
                </>
              )}

              {aiPersona === "친구" && (
                <>
                  <label className="text-xs text-gray-500 mb-1 block">
                    친구가 부를 이름 <span className="text-gray-400">(AI가 어르신을 부를 이름)</span>
                  </label>
                  <input
                    type="text"
                    value={friendName}
                    onChange={(e) => setFriendName(e.target.value)}
                    placeholder={`예: ${elderly.name}`}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-warm-300"
                  />
                  <p className="text-xs text-gray-400 mt-1">비워두면 어르신 실명({elderly.name})으로 부릅니다.</p>
                </>
              )}

              {/* 자동 호칭 미리보기 (손자·손녀·아들·딸) */}
              {(() => {
                const autoMap: Record<string, Record<string, string>> = {
                  "손자": { "남성": "할아버지", "여성": "할머니" },
                  "손녀": { "남성": "할아버지", "여성": "할머니" },
                  "아들": { "남성": "아버지",   "여성": "어머니" },
                  "딸":   { "남성": "아버지",   "여성": "어머니" },
                };
                const calling = autoMap[aiPersona]?.[gender];
                if (!calling) return null;
                return (
                  <p className="text-xs text-warm-600 bg-warm-50 rounded-lg px-3 py-2">
                    AI가 어르신을 <strong>"{calling}"</strong>이라고 자동으로 부릅니다.
                  </p>
                );
              })()}
            </div>
          </section>

          {/* AI 선제 메시지 */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700">💬 AI 먼저 보내는 메시지</h3>
              <button
                onClick={() => setProactiveEnabled((v: boolean) => !v)}
                className={`relative w-11 h-6 rounded-full transition-colors ${proactiveEnabled ? "bg-warm-500" : "bg-gray-200"}`}
              >
                <span className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${proactiveEnabled ? "translate-x-5" : "translate-x-0.5"}`} />
              </button>
            </div>

            {proactiveEnabled && (
              <div className="space-y-4">
                {/* 시간 범위 */}
                <div>
                  <p className="text-xs text-gray-500 mb-2">
                    메시지 보내는 시간대
                    <span className="ml-2 font-medium text-gray-700">{proactiveStart}시 ~ {proactiveEnd}시</span>
                  </p>
                  <div className="flex items-center gap-3">
                    <div className="flex-1">
                      <label className="text-xs text-gray-400 mb-1 block">시작</label>
                      <select
                        value={proactiveStart}
                        onChange={(e) => {
                          const v = Number(e.target.value);
                          setProactiveStart(v);
                          if (v >= proactiveEnd) setProactiveEnd(Math.min(v + 1, 23));
                        }}
                        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-warm-300"
                      >
                        {Array.from({ length: 24 }, (_, i) => (
                          <option key={i} value={i}>{i}시</option>
                        ))}
                      </select>
                    </div>
                    <span className="text-gray-400 mt-4">~</span>
                    <div className="flex-1">
                      <label className="text-xs text-gray-400 mb-1 block">종료</label>
                      <select
                        value={proactiveEnd}
                        onChange={(e) => {
                          const v = Number(e.target.value);
                          setProactiveEnd(v);
                          if (v <= proactiveStart) setProactiveStart(Math.max(v - 1, 0));
                        }}
                        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-warm-300"
                      >
                        {Array.from({ length: 24 }, (_, i) => (
                          <option key={i} value={i} disabled={i <= proactiveStart}>{i}시</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

                {/* 빈도 */}
                <div>
                  <p className="text-xs text-gray-500 mb-2">빈도</p>
                  <div className="flex gap-2">
                    {[
                      { label: "자주", value: 4 },
                      { label: "보통", value: 2 },
                      { label: "살짝 뜸하게", value: 1 },
                    ].map(({ label, value }) => (
                      <button
                        key={label}
                        onClick={() => setProactiveTimes(value)}
                        className={`flex-1 py-2 rounded-lg text-sm font-medium border transition-colors ${
                          proactiveTimes === value
                            ? "bg-warm-500 text-white border-warm-500"
                            : "bg-white text-gray-600 border-gray-200 hover:border-warm-300"
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>

                <p className="text-xs text-gray-400 bg-gray-50 rounded-lg px-3 py-2">
                  {proactiveStart}시~{proactiveEnd}시 사이에 하루 {proactiveTimes}번 AI가 먼저 말을 걸어드립니다.
                </p>
              </div>
            )}
          </section>

          {/* 약 복용 시간 */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-700">💊 약 복용 알림 시간</h3>
              <button
                onClick={addMedTime}
                disabled={medTimes.length >= 6}
                className="text-xs text-warm-500 hover:text-warm-600 disabled:opacity-40 flex items-center gap-1"
              >
                <Plus size={14} /> 추가
              </button>
            </div>
            {medTimes.length === 0 && (
              <p className="text-xs text-gray-400 text-center py-3">알림 시간이 없습니다.</p>
            )}
            <div className="space-y-2">
              {medTimes.map((t, i) => (
                <div key={i} className="flex items-center gap-2">
                  <input
                    type="time"
                    value={t}
                    onChange={(e) => updateMedTime(i, e.target.value)}
                    className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-warm-300"
                  />
                  <button
                    onClick={() => removeMedTime(i)}
                    className="text-gray-300 hover:text-red-400 transition-colors"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-400 mt-2">최대 6개, 설정한 시간에 AI가 약 복용 알림을 보냅니다.</p>
          </section>

          {/* 건강 상태 */}
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">🏥 건강 상태</h3>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={condInput}
                onChange={(e) => setCondInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addCondition()}
                placeholder="예: 당뇨, 고혈압"
                className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-warm-300"
              />
              <button
                onClick={addCondition}
                className="px-3 py-2 bg-warm-100 text-warm-600 rounded-lg text-sm hover:bg-warm-200 transition-colors"
              >
                추가
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {conditions.map((c) => (
                <span
                  key={c}
                  className="flex items-center gap-1 bg-gray-100 text-gray-700 text-xs px-3 py-1 rounded-full"
                >
                  {c}
                  <button onClick={() => removeCondition(c)} className="text-gray-400 hover:text-red-400 ml-1">
                    <X size={12} />
                  </button>
                </span>
              ))}
              {conditions.length === 0 && (
                <p className="text-xs text-gray-400">등록된 건강 상태가 없습니다.</p>
              )}
            </div>
          </section>
        </div>

        {/* 저장 버튼 */}
        <div className="px-6 py-4 border-t flex justify-end gap-2">
          <button onClick={onClose} className="btn-secondary text-sm">
            취소
          </button>
          <button onClick={handleSave} disabled={saving} className="btn-primary text-sm disabled:opacity-50">
            {saving ? "저장 중..." : "저장"}
          </button>
        </div>
      </div>
    </div>
  );
}
