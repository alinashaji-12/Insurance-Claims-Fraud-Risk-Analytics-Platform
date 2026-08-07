"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ClaimsTable } from "@/components/ClaimsTable";
import {
  ApiError,
  ClaimSummary,
  StatsMetrics,
  StatsSummary,
  fetchClaims,
  fetchStats,
  fetchStatsMetrics,
} from "@/lib/api";
import { formatScore } from "@/lib/utils";

type SortKey = "fraud_score" | "claim_amount" | "incident_date" | "claimant_name";

const FRAUD_RING_QUERY = "RING-";

function SummaryCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold tabular-nums text-slate-900">{value}</p>
      {hint ? <p className="mt-1 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}

function SkeletonCards() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="h-24 animate-pulse rounded-xl bg-slate-200/70" />
      ))}
    </div>
  );
}

function pct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<StatsSummary | null>(null);
  const [metrics, setMetrics] = useState<StatsMetrics | null>(null);
  const [items, setItems] = useState<ClaimSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [minScore, setMinScore] = useState("");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("fraud_score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [loading, setLoading] = useState(true);
  const [slowLoad, setSlowLoad] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setSlowLoad(false);
    setError(null);
    try {
      const [statsRes, claimsRes, metricsRes] = await Promise.all([
        fetchStats(),
        fetchClaims({
          status: status || undefined,
          min_score: minScore ? Number(minScore) : undefined,
          q: search || undefined,
          page,
          page_size: 25,
        }),
        fetchStatsMetrics().catch(() => null),
      ]);
      setStats(statsRes);
      setItems(claimsRes.items);
      setTotal(claimsRes.total);
      if (metricsRes) setMetrics(metricsRes);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Failed to load dashboard";
      setError(message);
    } finally {
      setLoading(false);
      setSlowLoad(false);
    }
  }, [page, status, minScore, search]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!loading) {
      setSlowLoad(false);
      return;
    }
    const t = window.setTimeout(() => setSlowLoad(true), 8_000);
    return () => window.clearTimeout(t);
  }, [loading]);

  const sortedItems = useMemo(() => {
    const copy = [...items];
    copy.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === "number" && typeof bv === "number") {
        return sortDir === "asc" ? av - bv : bv - av;
      }
      return sortDir === "asc"
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    });
    return copy;
  }, [items, sortKey, sortDir]);

  function onSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "claimant_name" ? "asc" : "desc");
    }
  }

  function applySearch(next: string) {
    setPage(1);
    setSearch(next.trim());
    setSearchInput(next.trim());
  }

  function showFraudRings() {
    applySearch(FRAUD_RING_QUERY);
    setStatus("");
    setMinScore("");
  }

  const pageCount = Math.max(1, Math.ceil(total / 25));
  const showingRings = search.toUpperCase().startsWith("RING");
  const fraud = metrics?.fraud_model;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
          Claims queue
        </h1>
        <p className="mt-1 max-w-2xl text-slate-600">
          Review incoming claims ranked by composite fraud risk (rules + XGBoost + anomaly).
        </p>
      </div>

      {error ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-amber-950">
          <p className="font-medium">API waking up or unreachable</p>
          <p className="mt-1 text-sm text-amber-900/90">{error}</p>
          <p className="mt-1 text-sm text-amber-900/80">
            Render free-tier services often sleep after idle and can take 30–60s to wake.
          </p>
          <button
            type="button"
            onClick={() => void load()}
            className="mt-3 rounded-lg bg-teal-800 px-3 py-1.5 text-sm font-semibold text-white hover:bg-teal-900"
          >
            Retry
          </button>
        </div>
      ) : null}

      {loading && !stats ? (
        <div className="space-y-3">
          <SkeletonCards />
          {slowLoad ? (
            <p className="text-sm text-slate-600">
              Still waiting on the API — Render free-tier services often sleep after idle and can
              take 30–60s to wake. Hang tight, or hit Retry once the timeout surfaces.
            </p>
          ) : null}
        </div>
      ) : stats ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <SummaryCard label="Total claims" value={stats.total_claims.toLocaleString()} />
          <SummaryCard
            label="High risk"
            value={stats.high_risk_count.toLocaleString()}
            hint="Score ≥ 60"
          />
          <SummaryCard
            label="Flagged / review"
            value={stats.flagged_count.toLocaleString()}
            hint="Score ≥ 35"
          />
          <SummaryCard label="Avg score" value={formatScore(stats.avg_score)} />
        </div>
      ) : null}

      {fraud && metrics?.available ? (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-sm font-semibold text-slate-800">Model metrics</h2>
            <p className="text-xs text-slate-500">From training holdout (fraud classifier)</p>
          </div>
          <dl className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">ROC-AUC</dt>
              <dd className="mt-0.5 text-lg font-semibold tabular-nums text-slate-900">
                {fraud.roc_auc != null ? fraud.roc_auc.toFixed(3) : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Precision</dt>
              <dd className="mt-0.5 text-lg font-semibold tabular-nums text-slate-900">
                {pct(fraud.precision)}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Recall</dt>
              <dd className="mt-0.5 text-lg font-semibold tabular-nums text-slate-900">
                {pct(fraud.recall)}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">F1</dt>
              <dd className="mt-0.5 text-lg font-semibold tabular-nums text-slate-900">
                {pct(fraud.f1)}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Accuracy</dt>
              <dd className="mt-0.5 text-lg font-semibold tabular-nums text-slate-900">
                {pct(fraud.accuracy)}
              </dd>
            </div>
          </dl>
        </div>
      ) : null}

      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="flex flex-[1.4] flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">Search</span>
            <input
              type="search"
              placeholder="Policy or claimant (e.g. RING-ALPHA-01)"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") applySearch(searchInput);
              }}
              className="rounded-lg border border-slate-300 px-3 py-2"
            />
          </label>
          <label className="flex flex-1 flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">Status</span>
            <select
              value={status}
              onChange={(e) => {
                setPage(1);
                setStatus(e.target.value);
              }}
              className="rounded-lg border border-slate-300 px-3 py-2"
            >
              <option value="">All</option>
              <option value="open">Open</option>
              <option value="review">Review</option>
              <option value="flagged">Flagged</option>
              <option value="pending">Pending</option>
            </select>
          </label>
          <label className="flex flex-1 flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">Min score</span>
            <input
              type="number"
              min={0}
              max={100}
              placeholder="e.g. 60"
              value={minScore}
              onChange={(e) => {
                setPage(1);
                setMinScore(e.target.value);
              }}
              className="rounded-lg border border-slate-300 px-3 py-2"
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => applySearch(searchInput)}
              className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-50"
            >
              Search
            </button>
            <button
              type="button"
              onClick={() => void load()}
              className="rounded-lg bg-teal-800 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-900"
            >
              Refresh
            </button>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={showFraudRings}
            className={`rounded-lg px-3 py-1.5 text-sm font-semibold ${
              showingRings
                ? "bg-rose-800 text-white"
                : "border border-rose-200 bg-rose-50 text-rose-900 hover:bg-rose-100"
            }`}
          >
            Show fraud rings
          </button>
          {search ? (
            <button
              type="button"
              onClick={() => applySearch("")}
              className="text-sm font-medium text-slate-600 underline-offset-2 hover:underline"
            >
              Clear search
            </button>
          ) : null}
          <p className="text-xs text-slate-500">
            Tip: open <span className="font-mono">RING-ALPHA-01</span> for the network graph demo.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="h-64 animate-pulse rounded-xl bg-slate-200/70" />
      ) : (
        <ClaimsTable
          items={sortedItems}
          sortKey={sortKey}
          sortDir={sortDir}
          onSort={onSort}
        />
      )}

      <div className="flex items-center justify-between text-sm text-slate-600">
        <p>
          Page {page} of {pageCount} · {total.toLocaleString()} claims
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={page <= 1 || loading}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 disabled:opacity-40"
          >
            Previous
          </button>
          <button
            type="button"
            disabled={page >= pageCount || loading}
            onClick={() => setPage((p) => p + 1)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
