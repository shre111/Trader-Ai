"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, pct, type RiskLevel, type Recommendation } from "@/lib/api";
import { ActionBadge, ScoreBar, PageHeader } from "@/components/ui";

const TYPES = ["ALL", "EQUITY", "MF"];

export default function Screener() {
  const [risk] = useState<RiskLevel>("balanced");
  const [rows, setRows] = useState<Recommendation[]>([]);
  const [type, setType] = useState("ALL");

  useEffect(() => { api.screener(risk).then(setRows).catch(() => setRows([])); }, [risk]);

  const shown = rows
    .filter((r) => type === "ALL" || r.sec_type === type)
    .sort((a, b) => b.final_score - a.final_score);

  return (
    <>
      <PageHeader title="Screener" right={
        <div style={{ display: "flex", gap: 6 }}>
          {TYPES.map((t) => (
            <button key={t} className={`chip ${t === type ? "chip-active" : ""}`} onClick={() => setType(t)}>{t}</button>
          ))}
        </div>
      } />

      <div className="card" style={{ overflow: "hidden" }}>
        <table>
          <thead><tr>
            <th>Security</th><th>Type</th><th>Action</th>
            <th style={{ textAlign: "right" }}>1Y Return</th><th style={{ textAlign: "right" }}>Volatility</th>
            <th style={{ textAlign: "right" }}>Sharpe</th><th style={{ width: 170 }}>Score</th>
          </tr></thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.symbol}>
                <td><Link href={`/security/${encodeURIComponent(r.symbol)}`} style={{ fontWeight: 500 }}>{r.name}</Link></td>
                <td className="muted">{r.sec_type}</td>
                <td><ActionBadge action={r.action} /></td>
                <td style={{ textAlign: "right" }}>{r.ret_1y != null ? pct(r.ret_1y) : "—"}</td>
                <td style={{ textAlign: "right" }}>{r.volatility != null ? pct(r.volatility, 0) : "—"}</td>
                <td style={{ textAlign: "right" }}>{r.sharpe != null ? r.sharpe.toFixed(2) : "—"}</td>
                <td><ScoreBar value={r.final_score} /></td>
              </tr>
            ))}
            {shown.length === 0 && <tr><td colSpan={7} className="muted" style={{ textAlign: "center", padding: 24 }}>No securities.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
