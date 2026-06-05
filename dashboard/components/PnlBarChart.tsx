"use client";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from "recharts";
import type { Trade } from "@/lib/api";

const TIP = { background: "rgba(8,14,40,0.95)", border: "1px solid rgba(99,179,237,0.2)", borderRadius: '10px', fontSize: 12, fontFamily: 'Inter', boxShadow: '0 8px 32px rgba(0,0,0,0.5)' };

export default function PnlBarChart({ trades }: { trades: Trade[] }) {
  if (!trades.length) return null;
  const data = trades.map((t, i) => ({ i: i + 1, pnl: t.pnl }));
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 5, right: 10, bottom: 8, left: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
        <XAxis dataKey="i" tick={{ fill: "#3d4f6e", fontSize: 9, fontFamily: 'Inter' }} label={{ value: "Trade #", position: "insideBottom", fill: "#2e3a5e", fontSize: 9, offset: -2 }} />
        <YAxis tick={{ fill: "#3d4f6e", fontSize: 9, fontFamily: 'Inter' }} tickFormatter={v => `₹${(v / 1000).toFixed(0)}K`} width={50} />
        <Tooltip contentStyle={TIP} formatter={(v: unknown) => [`₹${Number(v) >= 0 ? "+" : ""}${Number(v).toLocaleString("en-IN")}`, "P&L"]} />
        <ReferenceLine y={0} stroke="rgba(255,255,255,0.08)" />
        <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.pnl >= 0 ? "#10b981" : "#f43f5e"}
              style={{ filter: `drop-shadow(0 0 4px ${d.pnl >= 0 ? 'rgba(16,185,129,0.4)' : 'rgba(244,63,94,0.4)'})` }} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
