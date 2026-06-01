"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import axios from "axios";

const API = process.env.NEXT_PUBLIC_API_URL;

export default function HomePage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const endpoint = mode === "login" ? "/users/family/login" : "/users/family/register";
      const payload = mode === "login"
        ? { email: form.email, password: form.password }
        : form;

      const { data } = await axios.post(`${API}${endpoint}`, payload);
      localStorage.setItem("token", data.access_token);
      toast.success(mode === "login" ? "로그인되었습니다!" : "회원가입이 완료되었습니다!");
      router.push("/dashboard");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4 bg-gradient-to-b from-warm-50 to-warm-100">
      {/* 헤더 */}
      <div className="text-center mb-10">
        <div className="text-5xl mb-3">🌞</div>
        <h1 className="text-3xl font-bold text-warm-600">따뜻한하루</h1>
        <p className="text-gray-500 mt-2 text-sm">문자 한 통으로 가족이 되는 AI 케어 서비스</p>
      </div>

      {/* 로그인/회원가입 카드 */}
      <div className="card w-full max-w-sm">
        <div className="flex mb-6 bg-gray-100 rounded-lg p-1">
          {(["login", "register"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors ${
                mode === m ? "bg-white text-warm-600 shadow-sm" : "text-gray-500"
              }`}
            >
              {m === "login" ? "로그인" : "회원가입"}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === "register" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">이름</label>
              <input
                type="text"
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="홍길동"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-warm-300"
              />
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">이메일</label>
            <input
              type="email"
              required
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="example@email.com"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-warm-300"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">비밀번호</label>
            <input
              type="password"
              required
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              placeholder="••••••••"
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-warm-300"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full py-3 text-base disabled:opacity-60"
          >
            {loading ? "처리 중..." : mode === "login" ? "로그인" : "가입하기"}
          </button>
        </form>
      </div>

      {/* 서비스 소개 */}
      <div className="mt-12 grid grid-cols-3 gap-4 max-w-sm w-full text-center">
        {[
          { icon: "💬", title: "AI 문자 대화", desc: "가족처럼 따뜻한 일상 대화" },
          { icon: "💊", title: "건강 리마인더", desc: "약·식사 자동 알림" },
          { icon: "📊", title: "실시간 모니터링", desc: "감정·건강 트렌드 확인" },
        ].map((item) => (
          <div key={item.title} className="card py-4 px-2">
            <div className="text-2xl mb-1">{item.icon}</div>
            <div className="text-xs font-semibold text-gray-700">{item.title}</div>
            <div className="text-xs text-gray-400 mt-0.5">{item.desc}</div>
          </div>
        ))}
      </div>
    </main>
  );
}
