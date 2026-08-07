"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ScoreComponents } from "@/lib/api";

type Props = {
  breakdown: ScoreComponents | null | undefined;
};

export function ScoreBreakdownChart({ breakdown }: Props) {
  if (!breakdown) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 text-sm text-slate-500">
        No score breakdown available.
      </div>
    );
  }

  const data = [
    { name: "Rules", value: Number(breakdown.rules_weighted.toFixed(1)), fill: "#0f766e" },
    { name: "ML", value: Number(breakdown.ml_weighted.toFixed(1)), fill: "#1e3a5f" },
    { name: "Anomaly", value: Number(breakdown.anomaly_weighted.toFixed(1)), fill: "#b45309" },
  ];

  return (
    <div className="h-64 w-full rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="mb-2 text-sm font-semibold text-slate-800">Weighted score contribution</p>
      <ResponsiveContainer width="100%" height="85%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="name" tick={{ fill: "#475569", fontSize: 12 }} />
          <YAxis tick={{ fill: "#475569", fontSize: 12 }} domain={[0, "auto"]} />
          <Tooltip
            formatter={(value) => [`${value ?? 0}`, "Weighted points"]}
            contentStyle={{ borderRadius: 8, borderColor: "#cbd5e1" }}
          />
          <Bar dataKey="value" radius={[6, 6, 0, 0]}>
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
