"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type RiskLevel, type Recommendation } from "@/lib/api";
import { ActionBadge, ScoreBar, PageHeader } from "@/components/ui";

const RISKS: RiskLevel[] = ["conservative", "balanced", "aggressive"];
const FILTERS = ["ALL", "BUY", "HOLD", "SELL"] as const;

export default function Ideas() {
  const [risk, setRisk] = useState<RiskLevel>("balanced");
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("ALL");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.recommendations(risk).then((r) => { setRecs(r); setLoading(false); }).catch(() => setLoading(false));
  }, [risk]);

  const shown = recs.filter((r) => filter === "ALL" || r.action === filter);

  return (
    <>
      <PageHeader title="Recommendations" right={
        <div style={{ display: "flex", gap: 6 }}>
          {RISKS.map((r) => (
            <button key={r} className={`chip ${r === risk ? "chip-active" : ""}`} onClick={() => setRisk(r)} style={{ textTransform: "capitalize" }}>{r}</button>
          ))}
        </div>
      } />

      <div style={{ display: "flex", gap: 6, marginBottom: 14 }}>
        {FILTERS.map((f) => (
          <button key={f} className={`chip ${f === filter ? "chip-active" : ""}`} onClick={() => setFilter(f)}>{f}</button>
        ))}
      </div>

      <div className="card" style={{ overflow: "hidden" }}>
        <table>
          <thead><tr><th>Security</th><th>Category</th><th>Action</th><th style={{ textAlign: "right" }}>ML</th><th style={{ width: 190 }}>Score</th><th>Rationale</th></tr></thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.symbol}>
                <td>
                  <Link href={`/security/${encodeURIComponent(r.symbol)}`} style={{ fontWeight: 500 }}>{r.name}</Link>
                  <div className="muted" style={{ fontSize: 11 }}>{r.sec_type}</div>
                </td>
                <td className="muted">{r.category || "—"}</td>
                <td><ActionBadge action={r.action} /></td>
                <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>{(r.ml_prob * 100).toFixed(0)}%</td>
                <td><ScoreBar value={r.final_score} /></td>
                <td className="muted" style={{ fontSize: 13 }}>{r.rationale}</td>
              </tr>
            ))}
            {!loading && shown.length === 0 && <tr><td colSpan={6} className="muted" style={{ textAlign: "center", padding: 24 }}>No matches.</td></tr>}
          </tbody>
        </table>
      </div>
    </>
  );
}
