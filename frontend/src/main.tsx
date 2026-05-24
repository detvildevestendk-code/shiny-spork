import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

declare global {
  interface Window {
    __APP_CONFIG__?: { API_BASE_URL?: string; API_KEY?: string };
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

type DashboardData = {
  summary: DashboardSummary;
  health: Health;
  trades: Collection<Trade>;
  positions: Collection<Position>;
};

const apiBaseUrl = window.__APP_CONFIG__?.API_BASE_URL ?? import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const apiKey = window.__APP_CONFIG__?.API_KEY ?? import.meta.env.VITE_API_KEY ?? "";

function formatCurrency(value?: number | null) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(
    value ?? 0,
  );
}

function formatNumber(value?: number | null, digits = 4) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(value ?? 0);
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: apiKey ? { "x-api-key": apiKey } : {},
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${path} failed with ${response.status}: ${body || response.statusText}`);
  }
  return response.json() as Promise<T>;
}

function useDashboardData() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [summary, health, trades, positions] = await Promise.all([
        fetchJson<DashboardSummary>("/api/v1/dashboard/summary"),
        fetchJson<Health>("/api/v1/health"),
        fetchJson<Collection<Trade>>("/api/v1/trades"),
        fetchJson<Collection<Position>>("/api/v1/positions"),
      ]);
      setData({ summary, health, trades, positions });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown dashboard error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    const interval = window.setInterval(() => void load(), 30_000);
    return () => window.clearInterval(interval);
  }, []);

  return { data, loading, error, reload: load };
}

function App() {
  const { data, loading, error, reload } = useDashboardData();
  const summary = data?.summary;
  const balance = summary?.fake_balance;
  const positions = data?.positions.items ?? summary?.open_positions ?? [];
  const trades = data?.trades.items ?? summary?.trade_history ?? [];
  const healthChecks = data?.health.checks ?? {};
  const liveTradingEnabled = Boolean(summary?.live_trading_enabled);

  const cards = useMemo(
    () => [
      ["Paper Equity", formatCurrency(balance?.equity)],
      ["Available Balance", formatCurrency(balance?.available_balance)],
      ["Paper PnL", formatCurrency(summary?.live_pnl)],
      ["Open Positions", String(positions.length)],
      ["Risk Exposure", `${formatNumber(summary?.risk_exposure_pct, 2)}%`],
      ["AI Confidence", summary?.ai_confidence_score == null ? "N/A" : `${formatNumber(summary.ai_confidence_score * 100, 1)}%`],
    ],
    [balance, positions.length, summary],
  );

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-8 text-slate-100">
      <section className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-cyan-300">AI Futures Bot</p>
            <h1 className="mt-3 text-4xl font-semibold">Paper trading dashboard</h1>
            <p className="mt-3 max-w-3xl text-slate-400">
              Authenticated dashboard using backend paper simulation data. Live trading remains disabled and exchange
              connectivity is expected to stay in sandbox mode.
            </p>
          </div>
          <button
            onClick={() => void reload()}
            className="rounded-xl bg-cyan-400 px-4 py-2 font-semibold text-slate-950 hover:bg-cyan-300 disabled:opacity-60"
            disabled={loading}
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>

        <div className="mb-6 grid gap-3 lg:grid-cols-3">
          <StatusPill label="API" value={data?.health.status ?? (loading ? "loading" : "unknown")} ok={data?.health.status === "ok"} />
          <StatusPill label="Mode" value={summary?.mode ?? "paper"} ok={(summary?.mode ?? "paper") === "paper"} />
          <StatusPill label="Live Trading" value={liveTradingEnabled ? "enabled" : "disabled"} ok={!liveTradingEnabled} />
        </div>

        {error && (
          <div className="mb-6 rounded-2xl border border-rose-500/40 bg-rose-950/60 p-4 text-rose-100">
            <p className="font-semibold">Dashboard load error</p>
            <p className="mt-1 text-sm text-rose-200">{error}</p>
            {!apiKey && <p className="mt-2 text-sm text-rose-200">Missing API key in frontend runtime config.</p>}
          </div>
        )}

        {loading && !data ? (
          <LoadingGrid />
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
              {cards.map(([label, value]) => (
                <MetricCard key={label} label={label} value={value} />
              ))}
            </div>

            <div className="mt-8 grid gap-4 xl:grid-cols-3">
              <Panel title="Open paper positions" className="xl:col-span-2">
                <PositionsTable positions={positions} />
              </Panel>
              <Panel title="Health checks">
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
              <Panel title="Paper trade history" className="xl:col-span-2">
                <TradesTable trades={trades} />
              </Panel>
              <Panel title="Runtime config">
                <div className="space-y-3 text-sm text-slate-300">
                  <ConfigRow label="API base URL" value={apiBaseUrl} />
                  <ConfigRow label="API key" value={apiKey ? "configured" : "missing"} danger={!apiKey} />
                  <ConfigRow label="Data source" value="/api/v1/dashboard/summary, /health, /trades, /positions" />
                </div>
              </Panel>
            </div>
          </>
        )}
      </section>
    </main>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 shadow-xl">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function Panel({ title, children, className = "" }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-2xl border border-slate-800 bg-slate-900/70 p-5 ${className}`}>
      <h2 className="text-xl font-semibold">{title}</h2>
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
