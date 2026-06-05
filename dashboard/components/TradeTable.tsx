"use client";
import Badge from "./Badge";
import type { Trade } from "@/lib/api";
import { toDateStr, toISTTimeFull } from "@/lib/time";

const resultVariant = (r: string) => r === "TARGET" ? "green" : (r === "SL" || r === "TRAILING_SL") ? "red" : (r === "RL_EXIT" || r === "DQN_EXIT") ? "purple" : "yellow";
const fmt = (p: number) => `₹${p >= 0 ? "+" : ""}${p.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

export default function TradeTable({ trades, maxRows }: { trades: Trade[]; maxRows?: number }) {
  const rows = maxRows ? trades.slice(-maxRows).reverse() : [...trades].reverse();
  if (!rows.length) return <p className="text-sm text-center py-8" style={{ color: '#2e3a5e' }}>No trades to display</p>;
  return (
    <div className="overflow-x-auto">
      <table>
        <thead>
          <tr>{["Date", "Time", "Symbol", "Dir", "Strategy", "Entry", "Exit", "P&L", "Result", "Score", "Regime"].map(h => <th key={h}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((t, i) => (
            <tr key={i}>
              <td style={{ color: '#3d4f6e' }}>{toDateStr(String(t.entry_time))}</td>
              <td style={{ color: '#3d4f6e' }}>{toISTTimeFull(String(t.entry_time))}</td>
              <td style={{ color: '#a5b4fc', fontWeight: 600, textShadow: '0 0 8px rgba(165,180,252,0.3)' }}>{t.symbol}</td>
              <td><Badge label={t.direction} variant={t.direction === "CALL" ? "green" : "red"} /></td>
              <td style={{ color: '#5e7299' }}>{t.strategy?.replace(/_/g, " ")}</td>
              <td style={{ color: '#e8eeff' }}>₹{t.entry_premium?.toFixed(1)}</td>
              <td style={{ color: '#e8eeff' }}>₹{t.exit_premium?.toFixed(1) ?? "--"}</td>
              <td style={{ color: t.pnl > 0 ? '#34d399' : t.pnl < 0 ? '#fb7185' : '#5e7299', fontWeight: 700, textShadow: t.pnl !== 0 ? `0 0 8px ${t.pnl > 0 ? 'rgba(52,211,153,0.3)' : 'rgba(251,113,133,0.3)'}` : 'none' }}>{fmt(t.pnl)}</td>
              <td><Badge label={t.result} variant={resultVariant(t.result) as "green" | "red" | "yellow" | "blue" | "purple" | "gray"} /></td>
              <td style={{ color: '#e8eeff' }}>{(t.final_score * 100).toFixed(0)}%</td>
              <td style={{ color: '#5e7299' }}>{t.regime}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
