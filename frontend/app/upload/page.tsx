"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import { RiskScoreBadge } from "@/components/RiskScoreBadge";
import { ApiError, UploadResponse, uploadClaimsCsv } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

export default function UploadPage() {
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);

  const handleFile = useCallback(async (file: File | null) => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await uploadClaimsCsv(file);
      setResult(res);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Upload failed",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
          Bulk CSV upload
        </h1>
        <p className="mt-1 max-w-2xl text-slate-600">
          Drop a claims CSV to score each row instantly. Accepts the simple analyst schema or the
          Kaggle vehicle-fraud dataset columns.
        </p>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const file = e.dataTransfer.files?.[0] ?? null;
          void handleFile(file);
        }}
        className={`rounded-2xl border-2 border-dashed px-6 py-16 text-center transition ${
          dragging
            ? "border-teal-600 bg-teal-50"
            : "border-slate-300 bg-white shadow-sm"
        }`}
      >
        <p className="text-lg font-medium text-slate-800">Drag & drop a CSV here</p>
        <p className="mt-1 text-sm text-slate-500">or choose a file</p>
        <label className="mt-4 inline-flex cursor-pointer rounded-lg bg-teal-800 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-900">
          {loading ? "Scoring…" : "Select CSV"}
          <input
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            disabled={loading}
            onChange={(e) => void handleFile(e.target.files?.[0] ?? null)}
          />
        </label>
        <p className="mx-auto mt-4 max-w-lg text-xs text-slate-500">
          Required (simple): policy_number, claimant_name, claimant_phone, claimant_address,
          bank_account, vehicle_vin, incident_date, claim_type, claim_amount, repair_shop
        </p>
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-rose-800">
          <p className="font-semibold">Upload error</p>
          <p className="mt-1 text-sm whitespace-pre-wrap">{error}</p>
        </div>
      ) : null}

      {loading ? (
        <div className="h-40 animate-pulse rounded-xl bg-slate-200/70" />
      ) : null}

      {result ? (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-4 text-sm">
            <span className="rounded-lg bg-emerald-50 px-3 py-1 font-medium text-emerald-800">
              Accepted {result.accepted}
            </span>
            <span className="rounded-lg bg-rose-50 px-3 py-1 font-medium text-rose-800">
              Rejected {result.rejected}
            </span>
          </div>

          {result.results.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center text-slate-600">
              No scored rows returned.
            </div>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Row</th>
                    <th className="px-4 py-3">Claimant</th>
                    <th className="px-4 py-3">Amount</th>
                    <th className="px-4 py-3">Score</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Link</th>
                  </tr>
                </thead>
                <tbody>
                  {result.results.map((row) => (
                    <tr key={row.row_number} className="border-b border-slate-100">
                      <td className="px-4 py-3 tabular-nums">{row.row_number}</td>
                      <td className="px-4 py-3">
                        <div className="font-medium text-slate-900">{row.claimant_name || "—"}</div>
                        <div className="font-mono text-xs text-slate-500">{row.policy_number}</div>
                        {row.error ? (
                          <div className="mt-1 text-xs text-rose-700">{row.error}</div>
                        ) : null}
                      </td>
                      <td className="px-4 py-3 tabular-nums">
                        {formatCurrency(row.claim_amount)}
                      </td>
                      <td className="px-4 py-3">
                        {row.status === "error" ? (
                          <span className="text-rose-700">—</span>
                        ) : (
                          <RiskScoreBadge score={row.fraud_score} />
                        )}
                      </td>
                      <td className="px-4 py-3 capitalize">{row.status}</td>
                      <td className="px-4 py-3">
                        {row.claim_id ? (
                          <Link
                            href={`/claims/${row.claim_id}`}
                            className="font-medium text-teal-800 hover:underline"
                          >
                            Open
                          </Link>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}
