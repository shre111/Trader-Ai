"use client";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine } from "recharts";

interface Point { time: string; equity: number }
interface Props { curves: { low?: Point[]; medium?: Point[]; high?: Point[] }; selected?: "low" | "medium" | "high" | "all"; }

const COLORS = { low: "#06b6d4", medium: "#8b5cf6", high: "#10b981" };
const fmt = (v: number) => v >= 0 ? `₹+${v.toLocaleString("en-IN")}` : `₹${v.toLocaleString("en-IN")}`;

const TIP = { background: "rgba(8,14,40,0.95)", border: "1px solid rgba(99,179,237,0.2)", borderRadius: '10px', fontSize: 12, fontFamily: 'Inter', boxShadow: '0 8px 32px rgba(0,0,0,0.5), 0 0 20px rgba(6,182,212,0.1)' };
const AXIS = { fill: "#3d4f6e", fontSize: 10, fontFamily: 'Inter' };

export default function EquityChart({ curves, selected = "all" }: Props) {
  const maxLen = Math.max(curves.low?.length ?? 0, curves.medium?.length ?? 0, curves.high?.length ?? 0);
  if (maxLen === 0) return <div className="flex items-center justify-center h-48 text-sm" style={{ color: '#2e3a5e' }}>No equity data</div>;

  const data = Array.from({ length: maxLen }, (_, i) => ({
    i: i + 1,
    low:    curves.low?.[i]?.equity,
    medium: curves.medium?.[i]?.equity,
    high:   curves.high?.[i]?.equity,
  }));
  const show = (k: "low" | "medium" | "high") => selected === "all" || selected === k;

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 20, bottom: 8, left: 10 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
        <XAxis dataKey="i" tick={AXIS} label={{ value: "Trade #", position: "insideBottom", fill: "#2e3a5e", fontSize: 10, offset: -2 }} />
        <YAxis tick={AXIS} tickFormatter={v => `₹${(v / 1000).toFixed(0)}K`} width={55} />
        <Tooltip contentStyle={TIP} labelStyle={{ color: "#5e7299" }} formatter={(v: unknown) => [fmt(Number(v)), ""]} />
        <ReferenceLine y={0} stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
        <Legend wrapperStyle={{ fontSize: 11, color: "#5e7299", fontFamily: 'Inter' }} />
        {show("low")    && <Line type="monotone" dataKey="low"    stroke={COLORS.low}    dot={false} strokeWidth={2} name="Low"    connectNulls />}
        {show("medium") && <Line type="monotone" dataKey="medium" stroke={COLORS.medium} dot={false} strokeWidth={2} name="Medium" connectNulls />}
        {show("high")   && <Line type="monotone" dataKey="high"   stroke={COLORS.high}   dot={false} strokeWidth={2} name="High"   connectNulls />}
      </LineChart>
    </ResponsiveContainer>
  );
}
