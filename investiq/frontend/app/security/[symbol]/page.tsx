"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, inr, pct } from "@/lib/api";
import { ActionBadge, PageHeader } from "@/components/ui";

export default function SecurityDetail() {
  const params = useParams();
  const symbol = decodeURIComponent(String(params.symbol));
  const [data, setData] = useState<Record<string, any> | null>(null);
  const [amount, setAmount] = useState(10000);
  const [msg, setMsg] = useState("");

  useEffect(() => { api.security(symbol).then(setData).catch(() => setData(null)); }, [symbol]);

  if (!data || !data.security) return <div className="card" style={{ padding: 20 }}>Loading {symbol}…</div>;

  const sec = data.security, feat = data.features ?? {}, rec = data.recommendation ?? {}, fund = data.fundamentals ?? {};
  const buy = async () => { await api.buy(symbol, amount); setMsg(`Bought ${inr(amount)} of ${sec.name}`); };

  const rows: [string, number | undefined, "pct" | "num"][] = [
    ["1Y Return", feat.ret_1y, "pct"], ["3Y CAGR", feat.cagr_3y, "pct"],
    ["Volatility", feat.volatility, "pct"], ["Sharpe", feat.sharpe, "num"],
    ["Max Drawdown", feat.max_drawdown, "pct"], ["Beta", feat.beta, "num"],
    ["Momentum 12-1", feat.momentum_12_1, "pct"],
  ];

  return (
    <>
      <PageHeader title={sec.name} right={rec.action ? <ActionBadge action={rec.action} /> : undefined} />
      <div className="muted" style={{ marginTop: -12, marginBottom: 16 }}>{sec.symbol} · {sec.sec_type}{sec.category ? ` · ${sec.category}` : ""}</div>

      <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: 14 }}>
        <div className="card" style={{ padding: 18 }}>
          <strong>{sec.sec_type === "MF" ? "NAV" : "Price"} history</strong>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={data.history ?? []}>
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#94a3b8" }} minTickGap={50} />
              <YAxis tick={{ fontSize: 10, fill: "#94a3b8" }} width={52} domain={["auto", "auto"]} />
              <Tooltip contentStyle={{ borderRadius: 10, border: "1px solid #e7e9ee", fontSize: 12 }} />
              <Line type="monotone" dataKey="value" stroke="#4f46e5" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="card" style={{ padding: 18 }}>
          <strong>Factors</strong>
          <table style={{ marginTop: 8 }}>
            <tbody>
              {rows.map(([label, val, kind]) => (
                <tr key={label}>
                  <td className="muted">{label}</td>
                  <td style={{ textAlign: "right", fontWeight: 500 }}>
                    {val == null ? "—" : kind === "pct" ? pct(val) : val.toFixed(2)}
                  </td>
                </tr>
              ))}
              {sec.sec_type === "EQUITY" && (
                <>
                  <tr><td className="muted">PE</td><td style={{ textAlign: "right" }}>{fund.pe != null ? Number(fund.pe).toFixed(1) : "—"}</td></tr>
                  <tr><td className="muted">ROE</td><td style={{ textAlign: "right" }}>{fund.roe != null ? pct(fund.roe) : "—"}</td></tr>
                  <tr><td className="muted">Sector</td><td style={{ textAlign: "right" }}>{fund.sector ?? "—"}</td></tr>
                </>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card" style={{ padding: 18, marginTop: 16, display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <strong>Paper trade</strong>
        <input type="number" value={amount} onChange={(e) => setAmount(Number(e.target.value))} className="btn" style={{ width: 140 }} />
        <button className="btn btn-primary" onClick={buy}>Buy</button>
        {rec.rationale && <span className="muted" style={{ fontSize: 13 }}>{rec.rationale}</span>}
        {msg && <span className="pos" style={{ fontSize: 13 }}>{msg}</span>}
      </div>
    </>
  );
}
