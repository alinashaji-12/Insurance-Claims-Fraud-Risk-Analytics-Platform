"use client";

import Link from "next/link";
import { ClaimSummary } from "@/lib/api";
import { formatCurrency, isFraudRingPolicy } from "@/lib/utils";
import { RiskScoreBadge } from "@/components/RiskScoreBadge";

type SortKey = "fraud_score" | "claim_amount" | "incident_date" | "claimant_name";

type Props = {
  items: ClaimSummary[];
  sortKey: SortKey;
  sortDir: "asc" | "desc";
  onSort: (key: SortKey) => void;
};

function SortHeader({
  label,
  active,
  dir,
  onClick,
}: {
  label: string;
  active: boolean;
  dir: "asc" | "desc";
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1 font-semibold text-slate-700 hover:text-teal-800"
    >
      {label}
      <span className="text-xs text-slate-400">{active ? (dir === "asc" ? "↑" : "↓") : "↕"}</span>
    </button>
  );
}

export function ClaimsTable({ items, sortKey, sortDir, onSort }: Props) {
  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-16 text-center text-slate-600">
        No claims match these filters.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-4 py-3">
              <SortHeader
                label="Score"
                active={sortKey === "fraud_score"}
                dir={sortDir}
                onClick={() => onSort("fraud_score")}
              />
            </th>
            <th className="px-4 py-3">
              <SortHeader
                label="Claimant"
                active={sortKey === "claimant_name"}
                dir={sortDir}
                onClick={() => onSort("claimant_name")}
              />
            </th>
            <th className="px-4 py-3">Policy</th>
            <th className="px-4 py-3">Type</th>
            <th className="px-4 py-3">
              <SortHeader
                label="Amount"
                active={sortKey === "claim_amount"}
                dir={sortDir}
                onClick={() => onSort("claim_amount")}
              />
            </th>
            <th className="px-4 py-3">
              <SortHeader
                label="Incident"
                active={sortKey === "incident_date"}
                dir={sortDir}
                onClick={() => onSort("incident_date")}
              />
            </th>
            <th className="px-4 py-3">Status</th>
          </tr>
        </thead>
        <tbody>
          {items.map((claim) => {
            const ring = isFraudRingPolicy(claim.policy_number);
            return (
              <tr key={claim.id} className="border-b border-slate-100 hover:bg-teal-50/40">
                <td className="px-4 py-3">
                  <RiskScoreBadge score={claim.fraud_score} />
                </td>
                <td className="px-4 py-3">
                  <Link
                    href={`/claims/${claim.id}`}
                    className="font-medium text-slate-900 underline-offset-2 hover:text-teal-800 hover:underline"
                  >
                    {claim.claimant_name}
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="font-mono text-xs text-slate-600">{claim.policy_number}</span>
                    {ring ? (
                      <span
                        className="rounded bg-rose-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-rose-800"
                        title="Demo fraud ring — open for network graph"
                      >
                        Fraud ring
                      </span>
                    ) : null}
                  </div>
                </td>
                <td className="px-4 py-3 text-slate-700">{claim.claim_type}</td>
                <td className="px-4 py-3 tabular-nums text-slate-800">
                  {formatCurrency(claim.claim_amount)}
                </td>
                <td className="px-4 py-3 text-slate-600">{claim.incident_date}</td>
                <td className="px-4 py-3">
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs capitalize text-slate-700">
                    {claim.status}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
