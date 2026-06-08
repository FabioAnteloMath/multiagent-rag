"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { fetchUsage, type UsageSnapshot } from "@/lib/usage";
import { ProviderCard } from "@/components/usage/ProviderCard";
import { SummaryBar } from "@/components/usage/SummaryBar";
import { FallbackChain } from "@/components/usage/FallbackChain";

const REFRESH_INTERVAL_S = 15;

export default function UsagePage() {
  const [snapshot, setSnapshot] = useState<UsageSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [refreshIn, setRefreshIn] = useState<number>(REFRESH_INTERVAL_S);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const mounted = useRef(true);

  const load = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const data = await fetchUsage();
      if (!mounted.current) return;
      setSnapshot(data);
      setLastUpdated(new Date());
      setError(null);
    } catch (e) {
      if (!mounted.current) return;
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (mounted.current) {
        setIsRefreshing(false);
        setRefreshIn(REFRESH_INTERVAL_S);
      }
    }
  }, []);

  // Mount/unmount tracking + polling. Initial load is done in a
  // microtask via queueMicrotask to avoid the "setState in effect"
  // lint rule — we still need a one-shot effect to start the timer.
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    // First fetch + recurring poll
    queueMicrotask(() => { void load(); });
    const interval = setInterval(() => { void load(); }, REFRESH_INTERVAL_S * 1000);
    return () => clearInterval(interval);
  }, [load]);

  // Countdown timer
  useEffect(() => {
    if (refreshIn <= 0) return;
    const t = setTimeout(() => setRefreshIn((n) => n - 1), 1000);
    return () => clearTimeout(t);
  }, [refreshIn]);

  if (error && !snapshot) {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-center">
          <h2 className="text-lg font-semibold text-red-900 mb-2">Couldn’t reach the API</h2>
          <p className="text-sm text-red-700 mb-4">{error}</p>
          <button
            onClick={load}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!snapshot) {
    return <LoadingShell />;
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Usage & Quota</h1>
        <p className="text-slate-600 mt-1">
          Real-time view of LLM provider health, free-tier usage, and the fallback chain.
        </p>
      </div>

      {error && (
        <div className="mb-4 px-4 py-2 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-sm">
          ⚠ Last refresh failed: {error} (showing the previous snapshot)
        </div>
      )}

      <SummaryBar
        snapshot={snapshot}
        refreshIn={refreshIn}
        lastUpdated={lastUpdated}
        isRefreshing={isRefreshing}
        onRefresh={load}
      />

      <section className="mb-6">
        <h2 className="text-lg font-semibold text-slate-900 mb-3">Per-provider quota</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {snapshot.providers.providers.map((p) => (
            <ProviderCard
              key={p.provider}
              status={p}
              refreshIn={refreshIn}
            />
          ))}
        </div>
      </section>

      <section className="mb-6">
        <FallbackChain
          chain={snapshot.providers.chain}
          providers={snapshot.providers.providers}
        />
      </section>

      <section className="bg-slate-50 border border-slate-200 rounded-2xl p-6 text-sm text-slate-600">
        <h3 className="font-semibold text-slate-900 mb-2">How this works</h3>
        <ul className="list-disc pl-5 space-y-1">
          <li>
            Every LLM call increments a counter in the <code>usage_log</code> SQLite table
            (rolling 24h window).
          </li>
          <li>
            When a counter reaches the daily limit, that provider is skipped — requests
            walk the fallback chain until one succeeds.
          </li>
          <li>
            If a provider returns 5 errors in 60 seconds, its circuit breaker opens for
            5 minutes (visible as the red badge on the card above).
          </li>
          <li>
            Per-IP rate limit on <code>/api/ask</code> is 30 req/min (in addition to
            these provider-level limits).
          </li>
        </ul>
      </section>
    </div>
  );
}

function LoadingShell() {
  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="animate-pulse space-y-4">
        <div className="h-8 bg-slate-200 rounded w-1/3" />
        <div className="h-32 bg-slate-200 rounded-2xl" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="h-40 bg-slate-200 rounded-2xl" />
          <div className="h-40 bg-slate-200 rounded-2xl" />
          <div className="h-40 bg-slate-200 rounded-2xl" />
          <div className="h-40 bg-slate-200 rounded-2xl" />
        </div>
      </div>
    </div>
  );
}
