"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  api, inr, pct, signClass,
  type BacktestResp, type Holding, type MarketOverview, type PortfolioSummary, type Recommendation,
} from "@/lib/api";
import { StatCard, ActionBadge, PageHeader } from "@/components/ui";

export default function Dashboard() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [market, setMarket] = useState<MarketOverview | null>(null);
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [bt, setBt] = useState<BacktestResp | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [p, m, r, b] = await Promise.all([
          api.portfolio(), api.market(), api.recommendations("balanced"), api.backtest("balanced"),
        ]);
        setSummary(p.summary); setHoldings(p.holdings);
        setMarket(m); setRecs(r); setBt(b);
      } catch (e) { setErr(String(e)); }
    })();
  }, []);

  if (err) return <div className="card" style={{ padding: 20 }}>API error: {err}. Is the InvestIQ API running on :5055?</div>;

  const topBuys = recs.filter((r) => r.action === "BUY").slice(0, 6);

  return (
    <>
      <PageHeader title="Dashboard" right={<span className="muted" style={{ fontSize: 13 }}>Balanced profile</span>} />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 16 }}>
        <StatCard label="Portfolio Value" value={inr(summary?.total_value)} />
        <StatCard label="Total P&L" value={inr(summary?.pnl)} sub={pct(summary?.pnl_pct, 2)} tone={(summary?.pnl ?? 0) >= 0 ? "pos" : "neg"} />
        <StatCard label="Cash" value={inr(summary?.cash)} sub={`${summary?.n_holdings ?? 0} holdings`} />
        <StatCard
          label={market?.benchmark ?? "Nifty 50"}
          value={market?.last ? market.last.toLocaleString("en-IN", { maximumFractionDigits: 0 }) : "—"}
          sub={<span className={signClass(market?.change_1d)}>{pct(market?.change_1d, 2)} today</span>}
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: 14 }}>
        {/* Backtest equity curve */}
        <div className="card" style={{ padding: 18 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10 }}>
            <strong>Strategy vs Nifty</strong>
            <span className="muted" style={{ fontSize: 12 }}>
              {bt?.metrics?.cagr != null ? `CAGR ${pct(bt.metrics.cagr)} · benchmark ${pct(bt.metrics.benchmark_cagr)}` : ""}
            </span>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={bt?.equity_curve ?? []}>
              <defs>
                <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#4f46e5" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="#4f46e5" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#94a3b8" }} minTickGap={40} />
              <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} width={36} domain={["auto", "auto"]} />
              <Tooltip contentStyle={{ borderRadius: 10, border: "1px solid #e7e9ee", fontSize: 12 }} />
              <Area type="monotone" dataKey="benchmark" stroke="#94a3b8" strokeWidth={1.5} fill="none" />
              <Area type="monotone" dataKey="strategy" stroke="#4f46e5" strokeWidth={2} fill="url(#g)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Market breadth */}
        <div className="card" style={{ padding: 18 }}>
          <strong>Market Signal</strong>
          <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
            {(["BUY", "HOLD", "SELL"] as const).map((a) => (
              <div key={a} style={{ flex: 1, textAlign: "center", padding: "14px 0", borderRadius: 12, background: "#f8fafc", border: "1px solid var(--border)" }}>
                <div style={{ fontSize: 26, fontWeight: 700 }}>{market?.breadth?.[a] ?? 0}</div>
                <div style={{ marginTop: 4 }}><ActionBadge action={a} /></div>
              </div>
            ))}
          </div>
          <div className="muted" style={{ fontSize: 12, marginTop: 14 }}>
            Across the tracked universe under the balanced profile.
          </div>
        </div>
      </div>

      {/* Top recommendations */}
      <div className="card" style={{ marginTop: 16, overflow: "hidden" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 18px" }}>
          <strong>Top Recommendations</strong>
          <Link href="/ideas" style={{ color: "var(--primary)", fontSize: 13, fontWeight: 500 }}>View all →</Link>
        </div>
        <table>
          <thead><tr><th>Security</th><th>Type</th><th>Action</th><th style={{ textAlign: "right" }}>Score</th><th>Rationale</th></tr></thead>
          <tbody>
            {topBuys.map((r) => (
              <tr key={r.symbol}>
                <td><Link href={`/security/${encodeURIComponent(r.symbol)}`} style={{ fontWeight: 500 }}>{r.name}</Link></td>
                <td className="muted">{r.sec_type}</td>
                <td><ActionBadge action={r.action} /></td>
                <td style={{ textAlign: "right", fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>{r.final_score.toFixed(2)}</td>
                <td className="muted" style={{ fontSize: 13 }}>{r.rationale}</td>
              </tr>
            ))}
            {topBuys.length === 0 && <tr><td colSpan={5} className="muted" style={{ textAlign: "center", padding: 24 }}>No BUY signals right now.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
