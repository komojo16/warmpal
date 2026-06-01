"use client";
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement, LineElement,
  Tooltip, Legend, Filler,
} from "chart.js";
import { Line } from "react-chartjs-2";
import type { DailyEmotionPoint, EmotionLabel } from "@/lib/api";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

const EMOTION_SCORE: Record<EmotionLabel, number> = {
  positive: 3,
  neutral: 2,
  negative: 1,
  danger: 0,
};

const EMOTION_COLOR: Record<EmotionLabel, string> = {
  positive: "#22c55e",
  neutral:  "#94a3b8",
  negative: "#f59e0b",
  danger:   "#ef4444",
};

const EMOTION_KO: Record<EmotionLabel, string> = {
  positive: "긍정",
  neutral:  "보통",
  negative: "부정",
  danger:   "위험",
};

interface Props {
  data: DailyEmotionPoint[];
}

export default function EmotionChart({ data }: Props) {
  const labels = data.map((d) => d.date.slice(5)); // "04-08"
  const scores = data.map((d) => EMOTION_SCORE[d.emotion]);
  const pointColors = data.map((d) => EMOTION_COLOR[d.emotion]);

  const chartData = {
    labels,
    datasets: [
      {
        label: "감정 지수",
        data: scores,
        borderColor: "#ff5a1f",
        backgroundColor: "rgba(255,90,31,0.08)",
        pointBackgroundColor: pointColors,
        pointBorderColor: pointColors,
        pointRadius: 6,
        pointHoverRadius: 8,
        tension: 0.4,
        fill: true,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx: any) => {
            const point = data[ctx.dataIndex];
            return [
              ` 감정: ${EMOTION_KO[point.emotion]}`,
              ` 신뢰도: ${Math.round(point.score * 100)}%`,
              ` 대화 수: ${point.message_count}건`,
            ];
          },
        },
      },
    },
    scales: {
      y: {
        min: 0,
        max: 3,
        ticks: {
          stepSize: 1,
          callback: (v: number | string) => {
            const map: Record<number, string> = { 0: "위험", 1: "부정", 2: "보통", 3: "긍정" };
            return map[v as number] ?? "";
          },
        },
        grid: { color: "#f3f4f6" },
      },
      x: { grid: { display: false } },
    },
  };

  return (
    <div>
      <Line data={chartData} options={options as any} />
      <div className="flex gap-3 mt-3 justify-center flex-wrap">
        {(Object.entries(EMOTION_KO) as [EmotionLabel, string][]).map(([key, label]) => (
          <span key={key} className="flex items-center gap-1 text-xs text-gray-500">
            <span
              className="inline-block w-3 h-3 rounded-full"
              style={{ backgroundColor: EMOTION_COLOR[key] }}
            />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
}
