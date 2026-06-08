"use client";

import type { ProviderStatus } from "@/lib/usage";

const REASON: Record<string, string> = {
  groq:    "OpenAI-compatible, fastest inference. Default for chat routing.",
  gemini:  "Google AI Studio free tier. 1.5k/day. Fallback #1.",
  minimax: "Internal MiniMax API. Generous quota. Fallback #2.",
  ollama:  "Local model via Ollama. No network, no rate limit. Last resort fallback.",
};

export function FallbackChain({ chain, providers }: { chain: string[]; providers: ProviderStatus[] }) {
  const byName = new Map(providers.map((p) => [p.provider, p]));

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6">
      <h2 className="text-lg font-semibold text-slate-900 mb-1">Fallback chain</h2>
      <p className="text-sm text-slate-500 mb-5">
        When the requested provider is exhausted or returns an error, requests walk this chain in order.
      </p>

      <ol className="space-y-3">
        {chain.map((name, idx) => {
          const p = byName.get(name);
          if (!p) return null;

          const usable = !p.exhausted && p.circuit_open !== true;
          const dot = usable
            ? "bg-emerald-500"
            : p.circuit_open
            ? "bg-red-500 animate-pulse"
            : "bg-amber-500";

          return (
            <li key={name} className="flex items-start gap-3">
              <div className="flex flex-col items-center pt-1.5">
                <span className={`w-2.5 h-2.5 rounded-full ${dot}`} />
                {idx < chain.length - 1 && (
                  <span className="w-px h-8 bg-slate-200 mt-1" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-900 capitalize">
                    {idx + 1}. {name}
                  </span>
                  <StatusLabel
                    usable={usable}
                    exhausted={p.exhausted}
                    circuitOpen={p.circuit_open === true}
                  />
                </div>
                <p className="text-xs text-slate-500 mt-0.5">{REASON[name] ?? "Provider"}</p>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function StatusLabel({
  usable,
  exhausted,
  circuitOpen,
}: {
  usable: boolean;
  exhausted: boolean;
  circuitOpen: boolean;
}) {
  if (circuitOpen) {
    return <span className="text-xs text-red-600 font-medium">circuit open</span>;
  }
  if (exhausted) {
    return <span className="text-xs text-amber-600 font-medium">quota exhausted</span>;
  }
  if (usable) {
    return <span className="text-xs text-emerald-600 font-medium">available</span>;
  }
  return null;
}
