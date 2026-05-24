import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Position = {
  id?: string;
  symbol?: string;
  side?: string;
  amount?: number;
  entry_price?: number;
  mark_price?: number;
  unrealized_pnl?: number;
};

type DashboardSummary = {
  live_pnl?: number;
  open_positions?: Position[];
  risk_exposure_pct?: number;
  ai_confidence_score?: number | null;
  exchange_connection_status?: string;
  mode?: string;
  telegram_alerts_enabled?: boolean;
  live_trading_enabled?: boolean;
  exchange_sandbox?: boolean;
  [key: string]: unknown;
};

const DASHBOARD_SUMMARY_URL = "http://81.27.108.159:8000/api/v1/dashboard/summary";
const API_KEY = "testkey123";

function formatCurrency(value: number | undefined | null) {
  if (value == null || Number.isNaN(value)) return "-";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(value);
}

function formatPercent(value: number | undefined | null, multiplier = 1) {
  if (value == null || Number.isNaN(value)) return "-";
  return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value * multiplier)}%`;
}

function App() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function fetchDashboardSummary() {
      console.log("Fetching dashboard summary...");
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(DASHBOARD_SUMMARY_URL, {
          method: "GET",
          headers: {
            "x-api-key": API_KEY,
          },
          signal: controller.signal,
        });

        if (!response.ok) {
          const body = await response.text();
          throw new Error(`GET ${DASHBOARD_SUMMARY_URL} failed with ${response.status}: ${body || response.statusText}`);
        }

        const json = (await response.json()) as DashboardSummary;
        console.log("Dashboard API response:", json);
        setSummary(json);
      } catch (err) {
        if (controller.signal.aborted) return;
        console.error("Dashboard API fetch failed:", err);
        setError(err instanceof Error ? err.message : "Unknown dashboard API error");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void fetchDashboardSummary();
    return () => controller.abort();
  }, []);

  const openPositions = summary?.open_positions ?? [];
  const cards = useMemo(
    () => [
      ["Live PnL", formatCurrency(summary?.live_pnl)],
      ["Open Positions", loading ? "Loading..." : String(openPositions.length)],
      ["Risk Exposure", formatPercent(summary?.risk_exposure_pct)],
      ["AI Confidence", formatPercent(summary?.ai_confidence_score, 100)],
      ["Exchange", summary?.exchange_connection_status ?? (loading ? "Loading..." : "-")],
    ],
    [loading, openPositions.length, summary],
  );

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-8 text-slate-100">
      <section className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-cyan-300">AI Futures Bot</p>
            <h1 className="mt-3 text-4xl font-semibold">Live paper trading dashboard</h1>
            <p className="mt-3 max-w-3xl text-slate-400">
              Cards are populated from <code>{DASHBOARD_SUMMARY_URL}</code> using <code>x-api-key: testkey123</code>.
            </p>
          </div>
          <button
            onClick={() => window.location.reload()}
            className="rounded-xl bg-cyan-400 px-4 py-2 font-semibold text-slate-950 hover:bg-cyan-300"
          >
            Reload dashboard
          </button>
        </div>

        {error && (
          <div className="mb-6 rounded-2xl border border-rose-500/40 bg-rose-950/60 p-4 text-rose-100">
            <p className="font-semibold">Dashboard API error</p>
            <p className="mt-1 text-sm text-rose-200">{error}</p>
            <p className="mt-2 text-sm text-rose-200">Open the browser console for the matching console.error output.</p>
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-5">
          {cards.map(([label, value]) => (
            <MetricCard key={label} label={label} value={loading && value === "-" ? "Loading..." : value} loading={loading} />
          ))}
        </div>

        <div className="mt-8 grid gap-4 xl:grid-cols-3">
          <Panel title="Open positions" className="xl:col-span-2">
            {loading ? <LoadingText /> : <PositionsTable positions={openPositions} />}
          </Panel>
          <Panel title="Runtime status">
            <div className="space-y-3">
              <StatusPill label="Mode" value={summary?.mode ?? (loading ? "Loading..." : "-")} ok={summary?.mode === "paper"} />
              <StatusPill label="Live Trading" value={summary?.live_trading_enabled ? "enabled" : "disabled"} ok={!summary?.live_trading_enabled} />
              <StatusPill label="Sandbox" value={summary?.exchange_sandbox === false ? "disabled" : "enabled"} ok={summary?.exchange_sandbox !== false} />
              <StatusPill label="Telegram" value={summary?.telegram_alerts_enabled ? "enabled" : "disabled"} ok={Boolean(summary?.telegram_alerts_enabled)} />
            </div>
          </Panel>
        </div>

        <Panel title="Raw dashboard summary" className="mt-8">
          {loading ? <LoadingText /> : <pre className="overflow-x-auto rounded-xl bg-slate-950 p-4 text-sm text-slate-300">{JSON.stringify(summary, null, 2)}</pre>}
        </Panel>
      </section>
    </main>
  );
}

function MetricCard({ label, value, loading }: { label: string; value: string; loading?: boolean }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 shadow-xl">
      <p className="text-sm text-slate-400">{label}</p>
      {loading ? <div className="mt-3 h-8 w-24 animate-pulse rounded bg-slate-800" /> : <p className="mt-2 text-2xl font-semibold">{value}</p>}
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

function PositionsTable({ positions }: { positions: Position[] }) {
  if (!positions.length) return <p className="text-sm text-slate-400">No open positions returned by API.</p>;
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
          </tr>
        </thead>
        <tbody>
          {positions.map((position, index) => (
            <tr key={position.id ?? `${position.symbol}-${index}`} className="border-t border-slate-800">
              <td className="py-3 font-medium">{position.symbol ?? "-"}</td>
              <td className={position.side === "long" ? "text-emerald-300" : "text-rose-300"}>{position.side ?? "-"}</td>
              <td>{position.amount ?? "-"}</td>
              <td>{formatCurrency(position.entry_price)}</td>
              <td>{formatCurrency(position.mark_price)}</td>
              <td className={(position.unrealized_pnl ?? 0) >= 0 ? "text-emerald-300" : "text-rose-300"}>{formatCurrency(position.unrealized_pnl)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StatusPill({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-950/50 px-4 py-3">
      <span className="text-sm text-slate-400">{label}</span>
      <span className={`rounded-full px-3 py-1 text-xs font-semibold ${ok ? "bg-emerald-400/15 text-emerald-300" : "bg-amber-400/15 text-amber-300"}`}>
        {value}
      </span>
    </div>
  );
}

function LoadingText() {
  return <p className="animate-pulse text-sm text-slate-400">Loading backend data...</p>;
}

createRoot(document.getElementById("root")!).render(<App />);
