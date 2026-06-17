"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/ui";

export default function Settings() {
  const [profiles, setProfiles] = useState<Record<string, any>[]>([]);
  const [health, setHealth] = useState<Record<string, any> | null>(null);

  useEffect(() => {
    api.profiles().then(setProfiles).catch(() => {});
    api.health().then(setHealth).catch(() => {});
  }, []);

  return (
    <>
      <PageHeader title="Settings" />

      <div className="card" style={{ overflow: "hidden", marginBottom: 16 }}>
        <div style={{ padding: "14px 18px" }}><strong>Risk Profiles</strong></div>
        <table>
          <thead><tr>
            <th>Profile</th><th>Buy</th><th>Hold</th><th>Sell</th>
            <th>Max Holdings</th><th>Max Weight</th><th>Equity Target</th>
          </tr></thead>
          <tbody>
            {profiles.map((p) => (
              <tr key={String(p.level)}>
                <td style={{ fontWeight: 500, textTransform: "capitalize" }}>{p.name}</td>
                <td>{p.buy_threshold}</td><td>{p.hold_threshold}</td><td>{p.sell_threshold}</td>
                <td>{p.max_holdings}</td>
                <td>{(p.max_holding_weight * 100).toFixed(0)}%</td>
                <td>{(p.target_equity_weight * 100).toFixed(0)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card" style={{ padding: 18 }}>
        <strong>System</strong>
        <div className="muted" style={{ fontSize: 13, marginTop: 10, lineHeight: 2 }}>
          Model loaded: {health ? String(health.model_loaded) : "…"}<br />
          Securities: {health?.counts?.securities ?? "…"} · Feature rows: {health?.counts?.feature_rows ?? "…"}<br />
          Data sources: AMFI / mfapi.in / yfinance (free, delayed). Broker: paper only. Daily refresh at 18:30.
        </div>
      </div>
    </>
  );
}
