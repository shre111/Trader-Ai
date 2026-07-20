"use client";

import { useEffect, useState } from "react";
import { Area, AreaChart, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, pct, type RiskLevel, type BacktestResp } from "@/lib/api";
import { StatCard, PageHeader } from "@/components/ui";

const RISKS: RiskLevel[] = ["conservative", "balanced", "aggressive"];

export default function Backtest() {
  const [risk, setRisk] = useState<RiskLevel>("balanced");
  const [bt, setBt] = useState<BacktestResp | null>(null);

  useEffect(() => { api.backtest(risk).then(setBt).catch(() => setBt(null)); }, [risk]);

  const m = bt?.metrics ?? {};
  return (
    <>
      <PageHeader title="Backtest" right={
        <div style={{ display: "flex", gap: 6 }}>
          {RISKS.map((r) => (
            <button key={r} className={`chip ${r === risk ? "chip-active" : ""}`} onClick={() => setRisk(r)} style={{ textTransform: "capitalize" }}>{r}</button>
          ))}
        </div>
      } />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 16 }}>
        <StatCard label="Strategy CAGR" value={pct(m.cagr)} tone={(m.cagr ?? 0) >= 0 ? "pos" : "neg"} />
        <StatCard label="Benchmark CAGR" value={pct(m.benchmark_cagr)} />
        <StatCard label="Alpha (CAGR)" value={pct(m.alpha_cagr)} tone={(m.alpha_cagr ?? 0) >= 0 ? "pos" : "neg"} />
        <StatCard label="Sharpe" value={(m.sharpe ?? 0).toFixed(2)} sub={`Max DD ${pct(m.max_drawdown)}`} />
      </div>

      <div className="card" style={{ padding: 18 }}>
        <strong>Growth of ₹1 — Strategy vs Nifty</strong>
        <ResponsiveContainer width="100%" height={340}>
          <AreaChart data={bt?.equity_curve ?? []}>
            <defs>
              <linearGradient id="s" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#4f46e5" stopOpacity={0.25} />
                <stop offset="100%" stopColor="#4f46e5" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#94a3b8" }} minTickGap={50} />
            <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} width={42} domain={["auto", "auto"]} />
            <Tooltip contentStyle={{ borderRadius: 10, border: "1px solid #e7e9ee", fontSize: 12 }} />
            <Legend />
            <Area type="monotone" dataKey="benchmark" name="Nifty" stroke="#94a3b8" strokeWidth={1.5} fill="none" />
            <Area type="monotone" dataKey="strategy" name="Strategy" stroke="#4f46e5" strokeWidth={2} fill="url(#s)" />
          </AreaChart>
        </ResponsiveContainer>
        <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
          Monthly-rebalanced equal-weight top-{(m.n_periods ?? 0) > 0 ? "N" : "N"} factor-ranked portfolio (ML excluded to avoid lookahead).
        </div>
      </div>
    </>
  );
}
