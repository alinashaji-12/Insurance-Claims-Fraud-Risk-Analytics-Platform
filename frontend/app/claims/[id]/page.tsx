"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { FraudNetworkGraph } from "@/components/FraudNetworkGraph";
import { RiskScoreBadge } from "@/components/RiskScoreBadge";
import { isFraudRingPolicy } from "@/lib/utils";
import { ScoreBreakdownChart } from "@/components/ScoreBreakdownChart";
import {
  ApiError,
  ClaimDetail,
  NetworkResponse,
  fetchClaim,
  fetchNetwork,
} from "@/lib/api";
import { formatCurrency, formatScore } from "@/lib/utils";

export default function ClaimDetailPage() {
  const params = useParams();
  const claimId = Number(params.id);
  const [claim, setClaim] = useState<ClaimDetail | null>(null);
  const [network, setNetwork] = useState<NetworkResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isFinite(claimId) || claimId <= 0) {
      setError("Invalid claim id");
      setLoading(false);
      return;
    }

    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [detail, net] = await Promise.all([
          fetchClaim(claimId),
          fetchNetwork(claimId),
        ]);
        if (!cancelled) {
          setClaim(detail);
          setNetwork(net);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? err.message
              : err instanceof Error
                ? err.message
                : "Failed to load claim",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [claimId]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-10 w-64 animate-pulse rounded-lg bg-slate-200" />
        <div className="h-40 animate-pulse rounded-xl bg-slate-200" />
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="h-64 animate-pulse rounded-xl bg-slate-200" />
          <div className="h-64 animate-pulse rounded-xl bg-slate-200" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-6 text-amber-950">
        <p className="font-semibold">Could not load claim #{claimId}</p>
        <p className="mt-1 text-sm text-amber-900/90">{error}</p>
        <p className="mt-2 text-sm text-amber-900/80">
          If the API just woke from sleep, wait a few seconds and try again.
        </p>
        <Link href="/" className="mt-3 inline-block text-sm font-semibold underline">
          Back to dashboard
        </Link>
      </div>
    );
  }

  if (!claim) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-6 py-16 text-center text-slate-600">
        Claim not found.
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link href="/" className="text-sm font-medium text-teal-800 hover:underline">
            ← Claims queue
          </Link>
          <h1 className="mt-2 text-2xl font-semibold text-slate-900 sm:text-3xl">
            {claim.claimant_name}
          </h1>
          <p className="mt-1 text-slate-600">
            Policy {claim.policy_number}
            {isFraudRingPolicy(claim.policy_number) ? (
              <span className="ml-2 inline-block rounded bg-rose-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-rose-800">
                Fraud ring
              </span>
            ) : null}{" "}
            · {claim.claim_type} · {formatCurrency(claim.claim_amount)}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Fraud score
          </p>
          <div className="mt-1 flex items-center gap-3">
            <RiskScoreBadge score={claim.fraud_score} className="text-base" />
            <span className="text-sm capitalize text-slate-600">{claim.status}</span>
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm lg:col-span-1">
          <h2 className="text-sm font-semibold text-slate-800">Claim details</h2>
          <dl className="mt-3 space-y-2 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Incident</dt>
              <dd className="text-slate-800">{claim.incident_date}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Phone</dt>
              <dd className="font-mono text-xs text-slate-800">{claim.claimant_phone}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">VIN</dt>
              <dd className="font-mono text-xs text-slate-800">{claim.vehicle_vin}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Repair shop</dt>
              <dd className="text-right text-slate-800">{claim.repair_shop}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Address</dt>
              <dd className="text-right text-slate-800">{claim.claimant_address}</dd>
            </div>
          </dl>
          <p className="mt-4 text-sm leading-relaxed text-slate-600">{claim.description}</p>
        </div>

        <div className="lg:col-span-2">
          <ScoreBreakdownChart breakdown={claim.score_breakdown} />
          {claim.score_breakdown ? (
            <p className="mt-2 text-xs text-slate-500">
              Raw components — rules {formatScore(claim.score_breakdown.rules_score)} / ML P(fraud){" "}
              {(claim.score_breakdown.ml_probability * 100).toFixed(1)}% / anomaly{" "}
              {claim.score_breakdown.anomaly_flag ? "flagged" : "clear"}
            </p>
          ) : null}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-800">Why this score</h2>
          {claim.explanations.length === 0 && claim.rule_hits.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">No explanation factors available.</p>
          ) : (
            <ul className="mt-3 space-y-3">
              {claim.rule_hits.map((hit) => (
                <li
                  key={hit.rule_id}
                  className="rounded-lg border border-amber-100 bg-amber-50/60 px-3 py-2 text-sm text-amber-950"
                >
                  <span className="font-semibold">+{hit.points} pts</span> — {hit.reason}
                </li>
              ))}
              {claim.explanations.map((item) => (
                <li
                  key={`${item.feature}-${item.shap_value}`}
                  className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2 text-sm text-slate-800"
                >
                  {item.reason}
                </li>
              ))}
            </ul>
          )}
        </section>
        <FraudNetworkGraph network={network} />
      </div>
    </div>
  );
}
