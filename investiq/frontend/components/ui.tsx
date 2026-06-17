import React from "react";

export function StatCard({ label, value, sub, tone }: {
  label: string; value: React.ReactNode; sub?: React.ReactNode; tone?: "pos" | "neg";
}) {
  return (
    <div className="card" style={{ padding: "16px 18px" }}>
      <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 700 }} className={tone || ""}>{value}</div>
      {sub != null && <div style={{ fontSize: 12, marginTop: 4 }} className="muted">{sub}</div>}
    </div>
  );
}

export function ActionBadge({ action }: { action: string }) {
  const cls = action === "BUY" ? "badge-buy" : action === "SELL" ? "badge-sell" : "badge-hold";
  return <span className={`badge ${cls}`}>{action}</span>;
}

export function ScoreBar({ value }: { value: number }) {
  const pctV = Math.max(0, Math.min(1, value)) * 100;
  const color = value >= 0.6 ? "var(--positive)" : value >= 0.45 ? "var(--hold)" : "var(--negative)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 6, background: "#eef0f3", borderRadius: 999, overflow: "hidden", minWidth: 60 }}>
        <div style={{ width: `${pctV}%`, height: "100%", background: color }} />
      </div>
      <span style={{ fontVariantNumeric: "tabular-nums", fontSize: 12, fontWeight: 600 }}>{value.toFixed(2)}</span>
    </div>
  );
}

export function PageHeader({ title, right }: { title: string; right?: React.ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 22 }}>
      <h1>{title}</h1>
      {right}
    </div>
  );
}
