"use client";

import type { UsageSnapshot } from "@/lib/usage";

interface Props {
  snapshot: UsageSnapshot;
  refreshIn: number;
  lastUpdated: Date;
  isRefreshing: boolean;
  onRefresh: () => void;
}

export function SummaryBar({ snapshot, refreshIn, lastUpdated, isRefreshing, onRefresh }: Props) {
  const online = snapshot.providers.providers.filter(
    (p) => !p.exhausted && p.circuit_open !== true
  ).length;
  const total = snapshot.providers.providers.length;

  const totalUsed = snapshot.providers.providers
    .filter((p) => p.limit < 100_000) // skip ollama "unlimited"
    .reduce((acc, p) => acc + p.used, 0);
  const totalLimit = snapshot.providers.providers
    .filter((p) => p.limit < 100_000)
    .reduce((acc, p) => acc + p.limit, 0);
  const overallPct = totalLimit > 0 ? (totalUsed / totalLimit) * 100 : 0;

  return (
    <div className="bg-gradient-to-br from-slate-900 to-slate-800 text-white rounded-2xl p-6 mb-6">
      <div className="flex items-start justify-between mb-4 flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Provider health</h2>
          <p className="text-slate-400 text-sm mt-1">
            Quota & fallback state for the LLM providers powering this app
          </p>
        </div>
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-50 transition-colors text-sm"
        >
          <svg
            className={`w-4 h-4 ${isRefreshing ? "animate-spin" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          {isRefreshing ? "Refreshing…" : "Refresh now"}
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Stat
          label="Providers online"
          value={`${online} / ${total}`}
          accent={online === total ? "text-emerald-400" : "text-amber-400"}
        />
        <Stat
          label="Total requests (24h)"
          value={totalUsed.toLocaleString("en-US")}
          sub={`of ${totalLimit.toLocaleString("en-US")} combined`}
        />
        <Stat
          label="Quota used"
          value={`${overallPct.toFixed(1)}%`}
          sub={overallPct >= 85 ? "near limit" : "healthy"}
          accent={overallPct >= 85 ? "text-amber-400" : "text-emerald-400"}
        />
      </div>

      <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
        <span>
          Last updated: {lastUpdated.toLocaleTimeString("en-US", { hour12: false })} · auto-refresh in {refreshIn}s
        </span>
        {snapshot.enabled ? (
          <span className="inline-flex items-center gap-1 text-emerald-400">
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
            enforcement on
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-amber-400">
            <span className="w-1.5 h-1.5 bg-amber-400 rounded-full" />
            enforcement off
          </span>
        )}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
  accent = "text-white",
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
      <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">{label}</div>
      <div className={`text-2xl font-bold ${accent}`}>{value}</div>
      {sub && <div className="text-xs text-slate-400 mt-0.5">{sub}</div>}
    </div>
  );
}
