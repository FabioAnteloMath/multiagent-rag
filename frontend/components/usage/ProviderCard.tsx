"use client";

import type { ProviderStatus } from "@/lib/usage";

interface Props {
  status: ProviderStatus;
  refreshIn?: number; // seconds until next refresh (for label "refreshing in 9s")
}

const PROVIDER_META: Record<string, { label: string; color: string; icon: string }> = {
  groq:   { label: "Groq",         color: "from-orange-500 to-red-500",    icon: "⚡" },
  gemini: { label: "Google Gemini", color: "from-blue-500 to-indigo-500", icon: "✨" },
  minimax:{ label: "MiniMax",      color: "from-emerald-500 to-teal-500", icon: "🧠" },
  ollama: { label: "Ollama (local)", color: "from-slate-500 to-slate-700", icon: "🖥️" },
};

export function ProviderCard({ status, refreshIn }: Props) {
  const meta = PROVIDER_META[status.provider] ?? {
    label: status.provider,
    color: "from-slate-500 to-slate-700",
    icon: "•",
  };

  // For ollama, "limit" is 999999 — render that as "unlimited"
  const isUnlimited = status.limit >= 100_000;
  const pct = isUnlimited ? 0 : Math.min(100, (status.used / status.limit) * 100);

  // Colour threshold: green < 60%, yellow 60-85%, red > 85%
  let barColor = "bg-emerald-500";
  let textColor = "text-emerald-700";
  if (!isUnlimited) {
    if (pct >= 85) { barColor = "bg-red-500"; textColor = "text-red-700"; }
    else if (pct >= 60) { barColor = "bg-amber-500"; textColor = "text-amber-700"; }
  }

  const remainingLabel = isUnlimited
    ? "unlimited"
    : status.remaining.toLocaleString("en-US");
  const limitLabel = isUnlimited
    ? "∞"
    : status.limit.toLocaleString("en-US");
  const usedLabel = isUnlimited
    ? status.used.toLocaleString("en-US")
    : status.used.toLocaleString("en-US");

  // If the circuit is open, override visuals
  const circuitOpen = status.circuit_open === true;
  const circuitSeconds = status.circuit_open_for_s ?? 0;

  const cardRing = circuitOpen
    ? "ring-2 ring-red-300"
    : status.exhausted
    ? "ring-2 ring-red-200"
    : "";

  return (
    <div className={`bg-white border border-slate-200 rounded-2xl p-5 ${cardRing}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${meta.color} flex items-center justify-center text-white text-lg`}>
            {meta.icon}
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">{meta.label}</h3>
            <p className="text-xs text-slate-500">rolling {status.window_hours}h window</p>
          </div>
        </div>
        <CircuitBadge open={circuitOpen} seconds={circuitSeconds} />
      </div>

      {/* Bar */}
      <div className="mb-3">
        {isUnlimited ? (
          <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
            <div className="h-full w-1/3 bg-gradient-to-r from-slate-300 to-slate-400" />
          </div>
        ) : (
          <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full ${barColor} transition-all duration-500`}
              style={{ width: `${Math.max(2, pct)}%` }}
            />
          </div>
        )}
      </div>

      {/* Numbers */}
      <div className="flex items-baseline justify-between text-sm">
        <div>
          <span className={`font-semibold ${textColor}`}>{usedLabel}</span>
          <span className="text-slate-500"> / {limitLabel} used</span>
        </div>
        <div className="text-slate-500">
          <span className="font-medium text-slate-700">{remainingLabel}</span> left
        </div>
      </div>

      {pct >= 85 && !isUnlimited && !circuitOpen && (
        <p className="mt-3 text-xs text-red-600 font-medium">
          ⚠ Above 85% — fallback will trigger soon
        </p>
      )}
      {refreshIn !== undefined && (
        <p className="mt-2 text-[10px] text-slate-400">refreshing in {refreshIn}s</p>
      )}
    </div>
  );
}

function CircuitBadge({ open, seconds }: { open: boolean; seconds: number }) {
  if (!open) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
        <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full" /> online
      </span>
    );
  }
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-red-50 text-red-700 border border-red-200"
      title="Circuit breaker open — provider skipped for 5 minutes after repeated failures"
    >
      <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse" />
      circuit open · {m > 0 ? `${m}m${s.toString().padStart(2, "0")}s` : `${s}s`}
    </span>
  );
}
