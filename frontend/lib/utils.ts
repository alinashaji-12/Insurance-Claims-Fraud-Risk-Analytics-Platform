import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatScore(score: number | null | undefined): string {
  if (score == null || Number.isNaN(score)) return "—";
  return score.toFixed(1);
}

export type RiskLevel = "high" | "medium" | "low" | "unknown";

export function riskLevel(score: number | null | undefined): RiskLevel {
  if (score == null) return "unknown";
  if (score >= 60) return "high";
  if (score >= 35) return "medium";
  return "low";
}
