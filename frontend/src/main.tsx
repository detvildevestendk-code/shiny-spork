import React, { useEffect, useState } from "react";
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
  telegram_alerts_enabled?: boolean;
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

function valueOrDash(value: string | undefined | null) {
  return value && value.trim() ? value : "-";
}

function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadDashboardSummary() {
      console.log("Fetching dashboard summary...");
      setLoading(true);
      setError(null);

      try {
        const response = await fetch("http://81.27.108.159:8000/api/v1/dashboard/summary", {
          method: "GET",
          headers: {
            "x-api-key": "testkey123",
          },
          signal: controller.signal,
        });

        if (!response.ok) {
          const body = await response.text();
          throw new Error(`GET ${DASHBOARD_SUMMARY_URL} failed with ${response.status}: ${body || response.statusText}`);
        }

        const data = (await response.json()) as DashboardSummary;
        console.log("Dashboard API response:", data);
        setSummary(data);
      } catch (err) {
        if (controller.signal.aborted) return;
        console.error("Dashboard API fetch failed:", err);
        setError(err instanceof Error ? err.message : "Unknown dashboard API error");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void loadDashboardSummary();
    return () => controller.abort();
  }, []);

  const openPositions = summary?.open_positions ?? [];
  const cards = [
    ["Live PnL", formatCurrency(summary?.live_pnl)],
    ["Open Positions", loading ? "Loading..." : String(openPositions.length)],
    ["Risk Exposure", formatPercent(summary?.risk_exposure_pct)],
    ["AI Confidence", formatPercent(summary?.ai_confidence_score, 100)],
    ["Exchange", valueOrDash(summary?.exchange_connection_status)],
    ["Telegram Alerts", summary?.telegram_alerts_enabled == null ? "-" : summary.telegram_alerts_enabled ? "enabled" : "disabled"],
  ];

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-8 text-slate-100">
      <section className="mx-auto max-w-7xl">
        <div className="mb-8">
          <p className="text-sm uppercase tracking-[0.3em] text-cyan-300">AI Futures Bot</p>
          <h1 className="mt-3 text-4xl font-semibold">Live paper trading dashboard</h1>
          <p className="mt-3 max-w-3xl text-slate-400">
            Fetching live dashboard summary from <code>{DASHBOARD_SUMMARY_URL}</code>.
          </p>
        </div>

        {error && (
          <div className="mb-6 rounded-2xl border border-rose-500/40 bg-rose-950/60 p-4 text-rose-100">
            <p className="font-semibold">Dashboard API error</p>
            <p className="mt-1 text-sm text-rose-200">{error}</p>
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
          {cards.map(([label, value]) => (
            <MetricCard key={label} label={label} value={loading ? "Loading..." : value} />
          ))}
        </div>

        <div className="mt-8 grid gap-4 xl:grid-cols-3">
          <Panel title="Open positions" className="xl:col-span-2">
            {loading ? <p className="text-sm text-slate-400">Loading positions...</p> : <PositionsTable positions={openPositions} />}
          </Panel>
          <Panel title="Raw dashboard summary">
            {loading ? (
              <p className="text-sm text-slate-400">Loading summary...</p>
            ) : (
              <pre className="overflow-x-auto rounded-xl bg-slate-950 p-4 text-sm text-slate-300">{JSON.stringify(summary, null, 2)}</pre>
            )}
          </Panel>
        </div>
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
            <tr key={position.id ?? `${position.symbol ?? "position"}-${index}`} className="border-t border-slate-800">
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

createRoot(document.getElementById("root")!).render(<Dashboard />);
