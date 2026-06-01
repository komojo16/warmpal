"use client";
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement,
  Tooltip, Legend,
} from "chart.js";
import { Bar } from "react-chartjs-2";
import type { HealthTrendPoint } from "@/lib/api";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

interface Props {
  data: HealthTrendPoint[];
}

export default function HealthTrendChart({ data }: Props) {
  const labels = data.map((d) => d.date.slice(5) + " 주");

  const chartData = {
    labels,
    datasets: [
      {
        label: "약 복용률",
        data: data.map((d) => Math.round(d.medication_rate * 100)),
        backgroundColor: "rgba(255,90,31,0.7)",
        borderRadius: 6,
      },
      {
        label: "응답률",
        data: data.map((d) => Math.round(d.response_rate * 100)),
        backgroundColor: "rgba(99,102,241,0.7)",
        borderRadius: 6,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: "bottom" as const,
        labels: { font: { size: 12 } },
      },
      tooltip: {
        callbacks: {
          label: (ctx: any) => ` ${ctx.dataset.label}: ${ctx.parsed.y}%`,
        },
      },
    },
    scales: {
      y: {
        min: 0,
        max: 100,
        ticks: { callback: (v: any) => `${v}%` },
        grid: { color: "#f3f4f6" },
      },
      x: { grid: { display: false } },
    },
  };

  return <Bar data={chartData} options={options} />;
}
