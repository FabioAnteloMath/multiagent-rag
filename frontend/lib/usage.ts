const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8011/api';

export interface ProviderStatus {
  provider: string;
  used: number;
  limit: number;
  remaining: number;
  exhausted: boolean;
  window_hours: number;
  circuit_open?: boolean;
  circuit_open_for_s?: number;
}

export interface UsageSnapshot {
  enabled: boolean;
  providers: {
    chain: string[];
    providers: ProviderStatus[];
  };
  totals: {
    rows_logged: number;
  };
}

export async function fetchUsage(): Promise<UsageSnapshot> {
  const res = await fetch(`${API_BASE}/usage`, {
    cache: 'no-store',
  });
  if (!res.ok) {
    throw new Error(`Failed to load usage: ${res.status} ${res.statusText}`);
  }
  return res.json();
}
