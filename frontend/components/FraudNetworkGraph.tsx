"use client";

import dynamic from "next/dynamic";
import { NetworkResponse } from "@/lib/api";

const FraudNetworkGraphInner = dynamic(
  () => import("./FraudNetworkGraphInner").then((m) => m.FraudNetworkGraphInner),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-80 items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 text-sm text-slate-500">
        Loading network…
      </div>
    ),
  },
);

export function FraudNetworkGraph({ network }: { network: NetworkResponse | null }) {
  return <FraudNetworkGraphInner network={network} />;
}
