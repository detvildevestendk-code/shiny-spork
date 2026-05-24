import React, { useCallback, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

declare global {
  interface Window {
    __APP_CONFIG__?: { API_BASE_URL?: string; TRADING_API_KEY?: string; API_KEY?: string };
  }
}

type Balance = {
  equity?: number;
  available_balance?: number;
  used_margin?: number;
  realized_pnl?: number;
  unrealized_pnl?: number;
};

type Position = {
  id: string;
  symbol: string;
  side: string;
  amount: number;
  entry_price: number;
  mark_price: number;
  notional: number;
  unrealized_pnl: number;
  leverage: number;
  source?: string;
};

type Trade = {
  id: string;
  symbol: string;
  strategy_name: string;
  side: string;
  status: string;
  amount: number;
  entry_price: number;
  exit_price?: number | null;
  realized_pnl?: number | null;
  source?: string;
};

type DashboardSummary = {
  mode?: string;
  fake_balance?: Balance;
  live_pnl?: number;
  open_positions?: Position[];
  trade_history?: Trade[];
  risk_exposure_pct?: number;
  ai_confidence_score?: number | null;
  exchange_connection_status?: string;
  telegram_alerts_enabled?: boolean;
  live_trading_enabled?: boolean;
  exchange_sandbox?: boolean;
};

type Health = {
  status: string;
  checks?: Record<string, string>;
};

type Collection<T> = {
  mode?: string;
  items: T[];
  total: number;
};

type EndpointState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

type DashboardState = {
  summary: EndpointState<DashboardSummary>;
  health: EndpointState<Health>;
  trades: EndpointState<Collection<Trade>>;
  positions: EndpointState<Collection<Position>>;
};

type EndpointKey = keyof DashboardState;

const emptyState = <T,>(): EndpointState<T> => ({ data: null, loading: true, error: null });

const apiBaseUrl = window.__APP_CONFIG__?.API_BASE_URL ?? import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const tradingApiKey =
  window.__APP_CONFIG__?.TRADING_API_KEY ??
  window.__APP_CONFIG__?.API_KEY ??
  import.meta.env.VITE_TRADING_API_KEY ??
  import.meta.env.VITE_API_KEY ??
  "";

const endpoints: Record<EndpointKey, string> = {
  summary: "/api/v1/dashboard/summary",
  health: "/api/v1/health",
  trades: "/api/v1/trades",
  positions: "/api/v1/positions",
};

function formatCurrency(value?: number | null) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(
    value ?? 0,
  );
}

function formatNumber(value?: number | null, digits = 4) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(value ?? 0);
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function fetchJson<T>(path: string, retries = 2): Promise<T> {
  if (!tradingApiKey) {
    throw new Error("TRADING_API_KEY is missing from frontend runtime config");
  }

  let lastError: Error | null = null;
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      const response = await fetch(`${apiBaseUrl}${path}`, {
        headers: { "x-api-key": tradingApiKey },
      });
      if (!response.ok) {
        const body = await response.text();
        throw new Error(`${path} failed with ${response.status}: ${body || response.statusText}`);
      }
      return response.json() as Promise<T>;
    } catch (err) {
      lastError = err instanceof Error ? err : new Error("Unknown API request error");
      if (attempt < retries) {
        await sleep(400 * (attempt + 1));
      }
    }
  }
  throw lastError ?? new Error(`${path} failed`);
}

async function loadEndpoint<T>(path: string): Promise<EndpointState<T>> {
  try {
    return { data: await fetchJson<T>(path), loading: false, error: null };
  } catch (err) {
    return { data: null, loading: false, error: err instanceof Error ? err.message : "Unknown API error" };
  }
}

function useDashboardData() {
  const [state, setState] = useState<DashboardState>({
    summary: emptyState<DashboardSummary>(),
    health: emptyState<Health>(),
    trades: emptyState<Collection<Trade>>(),
    positions: emptyState<Collection<Position>>(),
  });
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    setRefreshing(true);
    setState((current) => ({
      summary: { ...current.summary, loading: true, error: null },
      health: { ...current.health, loading: true, error: null },
      trades: { ...current.trades, loading: true, error: null },
      positions: { ...current.positions, loading: true, error: null },
    }));

    const [summary, health, trades, positions] = await Promise.all([
      loadEndpoint<DashboardSummary>(endpoints.summary),
      loadEndpoint<Health>(endpoints.health),
      loadEndpoint<Collection<Trade>>(endpoints.trades),
      loadEndpoint<Collection<Position>>(endpoints.positions),
    ]);

    setState({ summary, health, trades, positions });
    setRefreshing(false);
  }, []);

  useEffect(() => {
    void load();
    const interval = window.setInterval(() => void load(), 30_000);
    return () => window.clearInterval(interval);
  }, [load]);

  return { state, refreshing, reload: load };
}

function App() {
  const { state, refreshing, reload } = useDashboardData();
  const summary = state.summary.data;
  const balance = summary?.fake_balance;
  const positions = state.positions.data?.items ?? summary?.open_positions ?? [];
  const trades = state.trades.data?.items ?? summary?.trade_history ?? [];
  const healthChecks = state.health.data?.checks ?? {};
  const liveTradingEnabled = Boolean(summary?.live_trading_enabled);
  const pageLoading = Object.values(state).every((endpoint) => endpoint.loading && !endpoint.data);
  const errors = Object.entries(state).filter(([, endpoint]) => endpoint.error);

  const cards = useMemo(
    () => [
      ["Paper Equity", formatCurrency(balance?.equity), state.summary.loading],
      ["Available Balance", formatCurrency(balance?.available_balance), state.summary.loading],
      ["Paper PnL", formatCurrency(summary?.live_pnl), state.summary.loading],
      ["Open Positions", String(positions.length), state.positions.loading],
      ["Risk Exposure", `${formatNumber(summary?.risk_exposure_pct, 2)}%`, state.summary.loading],
      ["AI Confidence", summary?.ai_confidence_score == null ? "N/A" : `${formatNumber(summary.ai_confidence_score * 100, 1)}%`, state.summary.loading],
    ],
    [balance, positions.length, state.positions.loading, state.summary.loading, summary],
  );

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-8 text-slate-100">
      <section className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-cyan-300">AI Futures Bot</p>
            <h1 className="mt-3 text-4xl font-semibold">Paper trading dashboard</h1>
            <p className="mt-3 max-w-3xl text-slate-400">
              Every dashboard request sends the <code>x-api-key</code> header from <code>TRADING_API_KEY</code>. Live
              trading remains disabled and exchange connectivity stays sandbox-only.
            </p>
          </div>
          <button
            onClick={() => void reload()}
            className="rounded-xl bg-cyan-400 px-4 py-2 font-semibold text-slate-950 hover:bg-cyan-300 disabled:opacity-60"
            disabled={refreshing}
          >
            {refreshing ? "Retrying..." : "Retry / Refresh"}
          </button>
        </div>

        <div className="mb-6 grid gap-3 lg:grid-cols-3">
          <StatusPill label="API" value={state.health.data?.status ?? (state.health.loading ? "loading" : "unknown")} ok={state.health.data?.status === "ok"} />
          <StatusPill label="Mode" value={summary?.mode ?? "paper"} ok={(summary?.mode ?? "paper") === "paper"} />
          <StatusPill label="Live Trading" value={liveTradingEnabled ? "enabled" : "disabled"} ok={!liveTradingEnabled} />
        </div>

        {errors.length > 0 && (
          <div className="mb-6 space-y-2 rounded-2xl border border-rose-500/40 bg-rose-950/60 p-4 text-rose-100">
            <p className="font-semibold">Some dashboard requests failed after retrying</p>
            {errors.map(([name, endpoint]) => (
              <p key={name} className="text-sm text-rose-200">
                <span className="font-semibold">{endpoints[name as EndpointKey]}</span>: {endpoint.error}
              </p>
            ))}
            {!tradingApiKey && <p className="text-sm text-rose-200">Missing TRADING_API_KEY in frontend runtime config.</p>}
          </div>
        )}

        {pageLoading ? (
          <LoadingGrid />
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
              {cards.map(([label, value, loading]) => (
                <MetricCard key={label as string} label={label as string} value={value as string} loading={Boolean(loading)} />
              ))}
            </div>

            <div className="mt-8 grid gap-4 xl:grid-cols-3">
              <Panel title="Open paper positions" className="xl:col-span-2" loading={state.positions.loading} error={state.positions.error}>
                <PositionsTable positions={positions} />
              </Panel>
              <Panel title="Health checks" loading={state.health.loading} error={state.health.error}>
                <div className="space-y-3">
                  {Object.keys(healthChecks).length === 0 ? (
                    <p className="text-sm text-slate-400">No readiness checks loaded yet.</p>
                  ) : (
                    Object.entries(healthChecks).map(([name, value]) => (
                      <StatusPill key={name} label={name} value={value} ok={value === "ok"} />
                    ))
                  )}
                  <StatusPill label="Exchange" value={summary?.exchange_connection_status ?? "sandbox"} ok />
                  <StatusPill label="Sandbox" value={summary?.exchange_sandbox ? "enabled" : "unknown"} ok={summary?.exchange_sandbox !== false} />
                  <StatusPill
                    label="Telegram"
                    value={summary?.telegram_alerts_enabled ? "enabled" : "disabled"}
                    ok={Boolean(summary?.telegram_alerts_enabled)}
                  />
                </div>
              </Panel>
            </div>

            <div className="mt-8 grid gap-4 xl:grid-cols-3">
              <Panel title="Paper trade history" className="xl:col-span-2" loading={state.trades.loading} error={state.trades.error}>
                <TradesTable trades={trades} />
              </Panel>
              <Panel title="Runtime config" loading={state.summary.loading} error={state.summary.error}>
                <div className="space-y-3 text-sm text-slate-300">
                  <ConfigRow label="API base URL" value={apiBaseUrl} />
                  <ConfigRow label="TRADING_API_KEY" value={tradingApiKey ? "configured" : "missing"} danger={!tradingApiKey} />
                  <ConfigRow label="Dashboard summary" value={endpoints.summary} />
                  <ConfigRow label="Health" value={endpoints.health} />
                  <ConfigRow label="Trades" value={endpoints.trades} />
                  <ConfigRow label="Positions" value={endpoints.positions} />
                </div>
              </Panel>
            </div>
          </>
        )}
      </section>
    </main>
  );
}

function MetricCard({ label, value, loading }: { label: string; value: string; loading?: boolean }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 shadow-xl">
      <p className="text-sm text-slate-400">{label}</p>
      {loading ? <div className="mt-3 h-7 w-24 animate-pulse rounded bg-slate-800" /> : <p className="mt-2 text-2xl font-semibold">{value}</p>}
    </div>
  );
}

function Panel({ title, children, className = "", loading = false, error }: { title: string; children: React.ReactNode; className?: string; loading?: boolean; error?: string | null }) {
  return (
    <section className={`rounded-2xl border border-slate-800 bg-slate-900/70 p-5 ${className}`}>
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-xl font-semibold">{title}</h2>
        {loading && <span className="text-xs text-cyan-300">Loading...</span>}
      </div>
      {error && <p className="mt-3 rounded-lg bg-rose-950/70 p-3 text-sm text-rose-200">{error}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}

function StatusPill({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900/70 px-4 py-3">
      <span className="text-sm text-slate-400">{label}</span>
      <span className={`rounded-full px-3 py-1 text-xs font-semibold ${ok ? "bg-emerald-400/15 text-emerald-300" : "bg-amber-400/15 text-amber-300"}`}>
        {value}
      </span>
    </div>
  );
}

function PositionsTable({ positions }: { positions: Position[] }) {
  if (!positions.length) return <p className="text-sm text-slate-400">No paper positions yet.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="text-slate-400">
          <tr>
            <th className="py-2">Symbol</th>
            <th>Side</th>
            <th>Amount</th>
            <th>Entry</th>
            <th>Mark</th>
            <th>Unrealized</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((position) => (
            <tr key={position.id} className="border-t border-slate-800">
              <td className="py-3 font-medium">{position.symbol}</td>
              <td className={position.side === "long" ? "text-emerald-300" : "text-rose-300"}>{position.side}</td>
              <td>{formatNumber(position.amount)}</td>
              <td>{formatCurrency(position.entry_price)}</td>
              <td>{formatCurrency(position.mark_price)}</td>
              <td className={position.unrealized_pnl >= 0 ? "text-emerald-300" : "text-rose-300"}>{formatCurrency(position.unrealized_pnl)}</td>
              <td className="text-slate-500">{position.source ?? "paper"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TradesTable({ trades }: { trades: Trade[] }) {
  if (!trades.length) return <p className="text-sm text-slate-400">No paper trades yet.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="text-slate-400">
          <tr>
            <th className="py-2">Symbol</th>
            <th>Strategy</th>
            <th>Side</th>
            <th>Status</th>
            <th>Entry</th>
            <th>Exit</th>
            <th>PnL</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((trade) => (
            <tr key={trade.id} className="border-t border-slate-800">
              <td className="py-3 font-medium">{trade.symbol}</td>
              <td>{trade.strategy_name}</td>
              <td className={trade.side === "long" ? "text-emerald-300" : "text-rose-300"}>{trade.side}</td>
              <td>{trade.status}</td>
              <td>{formatCurrency(trade.entry_price)}</td>
              <td>{trade.exit_price == null ? "-" : formatCurrency(trade.exit_price)}</td>
              <td className={(trade.realized_pnl ?? 0) >= 0 ? "text-emerald-300" : "text-rose-300"}>{trade.realized_pnl == null ? "-" : formatCurrency(trade.realized_pnl)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ConfigRow({ label, value, danger = false }: { label: string; value: string; danger?: boolean }) {
  return (
    <div>
      <p className="text-slate-500">{label}</p>
      <p className={danger ? "text-rose-300" : "break-words text-cyan-300"}>{value}</p>
    </div>
  );
}

function LoadingGrid() {
  return (
    <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
      {Array.from({ length: 6 }).map((_, index) => (
        <div key={index} className="h-28 animate-pulse rounded-2xl border border-slate-800 bg-slate-900/70" />
      ))}
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
