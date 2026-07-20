"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, inr, pct, signClass, type RiskLevel, type Holding, type PortfolioSummary } from "@/lib/api";
import { StatCard, PageHeader } from "@/components/ui";

export default function Portfolio() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [risk, setRisk] = useState<RiskLevel>("balanced");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const p = await api.portfolio();
    setSummary(p.summary); setHoldings(p.holdings);
  }, []);
  useEffect(() => { load(); }, [load]);

  const rebalance = async () => { setBusy(true); await api.rebalance(risk); await load(); setBusy(false); };
  const sell = async (sym: string) => { await api.sell(sym, 1); await load(); };

  return (
    <>
      <PageHeader title="Portfolio" right={
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <select value={risk} onChange={(e) => setRisk(e.target.value as RiskLevel)} className="btn" style={{ textTransform: "capitalize" }}>
            <option value="conservative">conservative</option>
            <option value="balanced">balanced</option>
            <option value="aggressive">aggressive</option>
          </select>
          <button className="btn btn-primary" onClick={rebalance} disabled={busy}>{busy ? "Rebalancing…" : "Rebalance"}</button>
        </div>
      } />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 16 }}>
        <StatCard label="Total Value" value={inr(summary?.total_value)} />
        <StatCard label="Invested" value={inr(summary?.invested)} />
        <StatCard label="Cash" value={inr(summary?.cash)} />
        <StatCard label="P&L" value={inr(summary?.pnl)} sub={pct(summary?.pnl_pct, 2)} tone={(summary?.pnl ?? 0) >= 0 ? "pos" : "neg"} />
      </div>

      <div className="card" style={{ overflow: "hidden" }}>
        <table>
          <thead><tr>
            <th>Holding</th><th style={{ textAlign: "right" }}>Units</th><th style={{ textAlign: "right" }}>Avg Cost</th>
            <th style={{ textAlign: "right" }}>Price</th><th style={{ textAlign: "right" }}>Value</th>
            <th style={{ textAlign: "right" }}>P&L</th><th style={{ textAlign: "right" }}>Weight</th><th></th>
          </tr></thead>
          <tbody>
            {holdings.map((h) => (
              <tr key={h.symbol}>
                <td><Link href={`/security/${encodeURIComponent(h.symbol)}`} style={{ fontWeight: 500 }}>{h.name || h.symbol}</Link></td>
                <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{h.units.toFixed(2)}</td>
                <td style={{ textAlign: "right" }}>{inr(h.avg_cost)}</td>
                <td style={{ textAlign: "right" }}>{inr(h.price)}</td>
                <td style={{ textAlign: "right" }}>{inr(h.value)}</td>
                <td style={{ textAlign: "right" }} className={signClass(h.pnl)}>{pct(h.pnl_pct, 1)}</td>
                <td style={{ textAlign: "right" }}>{(h.weight * 100).toFixed(1)}%</td>
                <td style={{ textAlign: "right" }}><button className="btn" onClick={() => sell(h.symbol)} style={{ padding: "4px 10px", fontSize: 12 }}>Sell</button></td>
              </tr>
            ))}
            {holdings.length === 0 && <tr><td colSpan={8} className="muted" style={{ textAlign: "center", padding: 24 }}>No holdings yet — click Rebalance to build a portfolio from current recommendations.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
