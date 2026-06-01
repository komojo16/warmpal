"use client";
import { useState } from "react";
import toast from "react-hot-toast";
import { X, Plus, Minus } from "lucide-react";
import api from "@/lib/api";

interface Props {
  onClose: () => void;
  onSuccess: () => void;
}

export default function RegisterElderlyModal({ onClose, onSuccess }: Props) {
  const [form, setForm] = useState({
    name: "",
    phone: "",
    nickname: "어르신",
    family_name: "자녀",
    gender: "여성",
    health_conditions: [""],
    medication_times: ["08:00"],
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload = {
        ...form,
        health_conditions: form.health_conditions.filter(Boolean),
        medication_times: form.medication_times.filter(Boolean),
        family_id: "",
      };
      await api.post("/users/elderly", payload);
      toast.success("어르신이 등록되었습니다!");
      onSuccess();
      onClose();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "등록에 실패했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const updateList = (key: "health_conditions" | "medication_times", idx: number, val: string) => {
    const arr = [...form[key]];
    arr[idx] = val;
    setForm({ ...form, [key]: arr });
  };

  const addItem = (key: "health_conditions" | "medication_times") =>
    setForm({ ...form, [key]: [...form[key], ""] });

  const removeItem = (key: "health_conditions" | "medication_times", idx: number) =>
    setForm({ ...form, [key]: form[key].filter((_, i) => i !== idx) });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-lg font-semibold">어르신 등록</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* 기본 정보 */}
          {[
            { label: "어르신 성함", key: "name", placeholder: "홍길동" },
            { label: "전화번호", key: "phone", placeholder: "+821012345678" },
            { label: "AI가 부를 호칭", key: "nickname", placeholder: "어르신" },
            { label: "어르신이 가족을 부를 호칭", key: "family_name", placeholder: "자녀" },
          ].map(({ label, key, placeholder }) => (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
              <input
                type="text"
                value={(form as any)[key]}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                placeholder={placeholder}
                required={["name", "phone"].includes(key)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-warm-300"
              />
            </div>
          ))}

          {/* 성별 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">어르신 성별</label>
            <div className="flex gap-3">
              {["여성", "남성"].map((g) => (
                <button
                  key={g}
                  type="button"
                  onClick={() => setForm({ ...form, gender: g })}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium border transition-colors ${
                    form.gender === g
                      ? "bg-warm-500 text-white border-warm-500"
                      : "bg-white text-gray-600 border-gray-200 hover:border-warm-300"
                  }`}
                >
                  {g === "여성" ? "👩 여성" : "👨 남성"}
                </button>
              ))}
            </div>
          </div>

          {/* 건강 상태 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">건강 상태</label>
            {form.health_conditions.map((cond, i) => (
              <div key={i} className="flex gap-2 mb-2">
                <input
                  type="text"
                  value={cond}
                  onChange={(e) => updateList("health_conditions", i, e.target.value)}
                  placeholder="예: 당뇨, 고혈압"
                  className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-warm-300"
                />
                <button type="button" onClick={() => removeItem("health_conditions", i)}
                  className="text-gray-400 hover:text-red-500">
                  <Minus size={16} />
                </button>
              </div>
            ))}
            <button type="button" onClick={() => addItem("health_conditions")}
              className="text-warm-500 text-sm flex items-center gap-1 hover:underline">
              <Plus size={14} /> 추가
            </button>
          </div>

          {/* 약 복용 시간 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">약 복용 시간</label>
            {form.medication_times.map((t, i) => (
              <div key={i} className="flex gap-2 mb-2">
                <input
                  type="time"
                  value={t}
                  onChange={(e) => updateList("medication_times", i, e.target.value)}
                  className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-warm-300"
                />
                <button type="button" onClick={() => removeItem("medication_times", i)}
                  className="text-gray-400 hover:text-red-500">
                  <Minus size={16} />
                </button>
              </div>
            ))}
            <button type="button" onClick={() => addItem("medication_times")}
              className="text-warm-500 text-sm flex items-center gap-1 hover:underline">
              <Plus size={14} /> 추가
            </button>
          </div>

          <button type="submit" disabled={loading}
            className="btn-primary w-full py-3 disabled:opacity-60">
            {loading ? "등록 중..." : "등록하기"}
          </button>
        </form>
      </div>
    </div>
  );
}
