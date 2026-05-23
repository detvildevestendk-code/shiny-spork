import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

declare global {
  interface Window {
    __APP_CONFIG__?: { API_BASE_URL?: string };
  }
}

const apiBaseUrl = window.__APP_CONFIG__?.API_BASE_URL ?? import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function App() {
  const cards = [
    ["Live PnL", "$0.00"],
    ["Open Positions", "0"],
    ["AI Confidence", "N/A"],
    ["Risk Exposure", "0%"],
    ["Exchange", "Not checked"],
    ["Telegram", "Disabled"],
  ];

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-8 text-slate-100">
      <section className="mx-auto max-w-6xl">
        <div className="mb-8">
          <p className="text-sm uppercase tracking-[0.3em] text-cyan-300">AI Futures Bot</p>
          <h1 className="mt-3 text-4xl font-semibold">Professional futures trading dashboard</h1>
          <p className="mt-3 max-w-2xl text-slate-400">
            API-ready React/Tailwind starter wired for live PnL, hedge-mode positions, AI scoring, risk exposure,
            strategy toggles, exchange health, and Telegram alert settings.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {cards.map(([label, value]) => (
            <div key={label} className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 shadow-xl">
              <p className="text-sm text-slate-400">{label}</p>
              <p className="mt-2 text-2xl font-semibold">{value}</p>
            </div>
          ))}
        </div>

        <div className="mt-8 grid gap-4 lg:grid-cols-2">
          <Panel title="Strategy toggles">
            {["EMA Crossover", "RSI Divergence", "Volume Breakout", "Trend Following", "Mean Reversion", "Scalping"].map(
              (name) => (
                <label key={name} className="flex items-center justify-between border-b border-slate-800 py-3">
                  <span>{name}</span>
                  <input type="checkbox" className="h-5 w-5 accent-cyan-400" defaultChecked={name.includes("EMA")} />
                </label>
              ),
            )}
          </Panel>
          <Panel title="API connection">
            <p className="text-slate-400">Backend base URL</p>
            <code className="mt-3 block rounded-lg bg-slate-950 p-3 text-cyan-300">{apiBaseUrl}</code>
            <p className="mt-4 text-sm text-slate-500">Connect this panel to /api/v1/dashboard/summary.</p>
          </Panel>
        </div>
      </section>
    </main>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
      <h2 className="text-xl font-semibold">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
