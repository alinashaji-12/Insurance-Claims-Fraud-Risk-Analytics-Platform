"use client";

import { useEffect, useMemo, useRef } from "react";
import ForceGraph2D, { ForceGraphMethods } from "react-force-graph-2d";
import { NetworkResponse } from "@/lib/api";
import { riskLevel } from "@/lib/utils";

type Props = {
  network: NetworkResponse | null;
};

const COLORS = {
  high: "#e11d48",
  medium: "#d97706",
  low: "#059669",
  unknown: "#64748b",
  focus: "#0f766e",
};

export function FraudNetworkGraphInner({ network }: Props) {
  const fgRef = useRef<ForceGraphMethods | undefined>(undefined);

  const graphData = useMemo(() => {
    if (!network) return { nodes: [], links: [] };
    return {
      nodes: network.nodes.map((n) => ({
        id: n.id,
        name: n.label,
        fraud_score: n.fraud_score,
        is_focus: n.is_focus,
        policy_number: n.policy_number,
      })),
      links: network.edges.map((e) => ({
        source: e.source,
        target: e.target,
        shared: e.shared_entities.map((s) => s.type).join(", "),
      })),
    };
  }, [network]);

  useEffect(() => {
    if (!fgRef.current || graphData.nodes.length === 0) return;
    const timer = setTimeout(() => {
      fgRef.current?.zoomToFit(400, 40);
    }, 300);
    return () => clearTimeout(timer);
  }, [graphData]);

  if (!network) {
    return (
      <div className="flex h-80 items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 text-sm text-slate-500">
        Loading network…
      </div>
    );
  }

  if (network.nodes.length === 0) {
    return (
      <div className="flex h-80 items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 text-sm text-slate-500">
        No linked claims found for this claim.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-4 py-3">
        <p className="text-sm font-semibold text-slate-800">Fraud network</p>
        <p className="text-xs text-slate-500">
          {network.nodes.length} nodes · {network.edges.length} links · {network.rings.length} ring
          {network.rings.length === 1 ? "" : "s"} (size ≥ 3)
        </p>
      </div>
      <div className="h-80 w-full">
        <ForceGraph2D
          ref={fgRef}
          graphData={graphData}
          height={320}
          backgroundColor="#ffffff"
          nodeLabel={(node) => {
            const n = node as {
              name?: string;
              fraud_score?: number | null;
              policy_number?: string | null;
            };
            return `${n.name ?? ""}\nScore: ${n.fraud_score ?? "—"}\n${n.policy_number ?? ""}`;
          }}
          linkLabel={(link) => String((link as { shared?: string }).shared ?? "")}
          nodeCanvasObject={(node, ctx, globalScale) => {
            const n = node as {
              x?: number;
              y?: number;
              name?: string;
              fraud_score?: number | null;
              is_focus?: boolean;
            };
            const x = n.x ?? 0;
            const y = n.y ?? 0;
            const level = riskLevel(n.fraud_score ?? null);
            const color = n.is_focus ? COLORS.focus : COLORS[level];
            const r = n.is_focus ? 8 : 5;
            ctx.beginPath();
            ctx.arc(x, y, r, 0, 2 * Math.PI, false);
            ctx.fillStyle = color;
            ctx.fill();
            const label = (n.name ?? "").split(" ")[0] ?? "";
            const fontSize = 12 / globalScale;
            ctx.font = `${fontSize}px Sans-Serif`;
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            ctx.fillStyle = "#334155";
            ctx.fillText(label, x, y + r + 1);
          }}
          linkColor={() => "#94a3b8"}
          linkWidth={1.5}
          cooldownTicks={80}
        />
      </div>
    </div>
  );
}
