import { cn, formatScore, riskLevel } from "@/lib/utils";

type Props = {
  score: number | null | undefined;
  className?: string;
};

const STYLES = {
  high: "bg-rose-100 text-rose-800 ring-rose-200",
  medium: "bg-amber-100 text-amber-900 ring-amber-200",
  low: "bg-emerald-100 text-emerald-800 ring-emerald-200",
  unknown: "bg-slate-100 text-slate-600 ring-slate-200",
} as const;

export function RiskScoreBadge({ score, className }: Props) {
  const level = riskLevel(score);
  return (
    <span
      className={cn(
        "inline-flex min-w-[3.5rem] items-center justify-center rounded-md px-2 py-0.5 text-sm font-semibold tabular-nums ring-1 ring-inset",
        STYLES[level],
        className,
      )}
      title={level === "unknown" ? "Not scored yet" : `${level} risk`}
    >
      {formatScore(score)}
    </span>
  );
}
