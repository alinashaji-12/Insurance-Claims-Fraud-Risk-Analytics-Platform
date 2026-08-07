/** Typed API client for ClaimGuard AI backend. */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

/** Render free-tier cold starts often take 30–60s; abort so the UI can prompt Retry. */
const DEFAULT_TIMEOUT_MS = 55_000;

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function isAbortError(err: unknown): boolean {
  return (
    (err instanceof DOMException && err.name === "AbortError") ||
    (err instanceof Error && err.name === "AbortError")
  );
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const timeoutMs = DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const externalSignal = init?.signal;
  const onExternalAbort = () => controller.abort();
  if (externalSignal) {
    if (externalSignal.aborted) {
      controller.abort();
    } else {
      externalSignal.addEventListener("abort", onExternalAbort, { once: true });
    }
  }
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...init?.headers,
      },
      cache: "no-store",
    });

    let body: unknown = null;
    const text = await res.text();
    if (text) {
      try {
        body = JSON.parse(text);
      } catch {
        body = text;
      }
    }

    if (!res.ok) {
      let detail = res.statusText;
      if (typeof body === "object" && body && "detail" in body) {
        const raw = (body as { detail: unknown }).detail;
        detail = Array.isArray(raw)
          ? raw
              .map((item) =>
                typeof item === "object" && item && "msg" in item
                  ? String((item as { msg: unknown }).msg)
                  : String(item),
              )
              .join("; ")
          : String(raw);
      }
      throw new ApiError(detail || `Request failed (${res.status})`, res.status, body);
    }

    return body as T;
  } catch (err) {
    if (isAbortError(err) && !externalSignal?.aborted) {
      throw new ApiError(
        "API is waking up or unreachable (Render free tier can take ~30–60s). Click Retry.",
        408,
        { detail: "timeout" },
      );
    }
    if (err instanceof TypeError) {
      throw new ApiError(
        "Cannot reach the API. It may be waking from sleep — wait a moment and Retry.",
        0,
        { detail: "network" },
      );
    }
    throw err;
  } finally {
    clearTimeout(timer);
    externalSignal?.removeEventListener("abort", onExternalAbort);
  }
}

export type ClaimSummary = {
  id: number;
  policy_number: string;
  claimant_name: string;
  claim_type: string;
  claim_amount: number;
  incident_date: string;
  fraud_score: number | null;
  fraud_label: boolean | null;
  status: string;
  repair_shop: string;
  submitted_at: string;
};

export type ScoreComponents = {
  rules_score: number;
  rules_weighted: number;
  ml_probability: number;
  ml_weighted: number;
  anomaly_flag: boolean;
  anomaly_score: number;
  anomaly_weighted: number;
};

export type ExplanationItem = {
  feature: string;
  importance: number;
  shap_value: number;
  reason: string;
};

export type RuleHit = {
  rule_id: string;
  points: number;
  reason: string;
};

export type ClaimDetail = ClaimSummary & {
  claimant_phone: string;
  claimant_address: string;
  bank_account: string;
  vehicle_vin: string;
  description: string;
  age: number | null;
  vehicle_category: string | null;
  vehicle_price_band: string | null;
  accident_area: string | null;
  fault: string | null;
  past_number_of_claims: string | null;
  police_report_filed: string | null;
  witness_present: string | null;
  days_policy_claim: string | null;
  address_change_claim: string | null;
  make: string | null;
  score_breakdown: ScoreComponents | null;
  rule_hits: RuleHit[];
  explanations: ExplanationItem[];
  weights: Record<string, number> | null;
};

export type ClaimsListResponse = {
  items: ClaimSummary[];
  total: number;
  page: number;
  page_size: number;
};

export type StatsSummary = {
  total_claims: number;
  flagged_count: number;
  high_risk_count: number;
  avg_score: number;
  fraud_label_count: number;
  pending_score_count: number;
};

export type ModelMetrics = {
  precision?: number | null;
  recall?: number | null;
  f1?: number | null;
  roc_auc?: number | null;
  accuracy?: number | null;
  contamination?: number | null;
  anomaly_rate?: number | null;
};

export type StatsMetrics = {
  fraud_model: ModelMetrics | null;
  anomaly_model: ModelMetrics | null;
  available: boolean;
  message: string | null;
};

export type NetworkNode = {
  id: number;
  claim_id: number;
  label: string;
  fraud_score: number | null;
  policy_number: string | null;
  is_focus: boolean;
};

export type NetworkEdge = {
  source: number;
  target: number;
  shared_entities: Array<{ type: string; value: string }>;
};

export type NetworkResponse = {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  rings: Array<{ claim_ids: number[]; size: number }>;
  focus_claim_id: number | null;
};

export type UploadResponse = {
  accepted: number;
  rejected: number;
  results: Array<{
    row_number: number;
    policy_number: string;
    claimant_name: string;
    claim_amount: number;
    fraud_score: number;
    status: string;
    claim_id: number | null;
    error: string | null;
  }>;
  errors: string[];
};

export function getApiBase(): string {
  return API_BASE;
}

export function fetchClaims(params: {
  status?: string;
  min_score?: number;
  q?: string;
  page?: number;
  page_size?: number;
}): Promise<ClaimsListResponse> {
  const q = new URLSearchParams();
  if (params.status) q.set("status", params.status);
  if (params.min_score != null) q.set("min_score", String(params.min_score));
  if (params.q?.trim()) q.set("q", params.q.trim());
  q.set("page", String(params.page ?? 1));
  q.set("page_size", String(params.page_size ?? 25));
  return request<ClaimsListResponse>(`/claims?${q.toString()}`);
}

export function fetchClaim(id: number): Promise<ClaimDetail> {
  return request<ClaimDetail>(`/claims/${id}`);
}

export function fetchStats(): Promise<StatsSummary> {
  return request<StatsSummary>("/stats/summary");
}

export function fetchStatsMetrics(): Promise<StatsMetrics> {
  return request<StatsMetrics>("/stats/metrics");
}

export function fetchNetwork(claimId: number): Promise<NetworkResponse> {
  return request<NetworkResponse>(`/network/${claimId}`);
}

export async function uploadClaimsCsv(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  return request<UploadResponse>("/claims/upload", { method: "POST", body: form });
}
