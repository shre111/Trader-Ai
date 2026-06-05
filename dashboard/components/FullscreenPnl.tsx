"use client";
import { useEffect, useState, useCallback } from "react";
import { X } from "lucide-react";
import { fetchJSON, type BacktestResults, type LiveState } from "@/lib/api";

const pnlFmt = (v: number) => `${v >= 0 ? "+" : ""}${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;

export default function FullscreenPnl({ onClose }: { onClose: () => void }) {
  const [pnl, setPnl]         = useState(0);
  const [winRate, setWinRate] = useState("--");
  const [trades, setTrades]   = useState(0);
  const [regime, setRegime]   = useState("--");
  const [price, setPrice]     = useState(0);
  const [time, setTime]       = useState("--:--:--");

  const load = useCallback(async () => {
    const [results, live] = await Promise.all([
      fetchJSON<BacktestResults>("/api/backtest/results").catch(() => ({})),
      fetchJSON<LiveState>("/api/state").catch(() => null),
    ]);
    const high = (results as BacktestResults).high;
    if (high) { setPnl(high.pnl); setWinRate(`${high.win_rate}%`); setTrades(high.trades); }
    if (live) { setRegime(live.regime); setPrice(live.last_price); }
    setTime(new Date().toLocaleTimeString("en-IN", { hour12: false }));
  }, []);

  useEffect(() => { load(); const id = setInterval(load, 3000); return () => clearInterval(id); }, [load]);
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape" || e.key === "F11") { e.preventDefault(); onClose(); } };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const isPositive = pnl >= 0;
  return (
    <div className="fullscreen-pnl">
      {/* Ambient glow orbs */}
      <div style={{ position: 'absolute', top: '20%', left: '15%', width: 400, height: 400, borderRadius: '50%', background: 'radial-gradient(circle, rgba(99,102,241,0.08), transparent 70%)', filter: 'blur(40px)', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', bottom: '20%', right: '15%', width: 350, height: 350, borderRadius: '50%', background: `radial-gradient(circle, ${isPositive ? 'rgba(16,185,129,0.1)' : 'rgba(244,63,94,0.1)'}, transparent 70%)`, filter: 'blur(40px)', pointerEvents: 'none' }} />

      <button onClick={onClose} className="absolute top-6 right-6 z-10 transition-all interactive"
        style={{ color: '#2e3a5e', background: 'rgba(255,255,255,0.05)', borderRadius: '10px', padding: '8px', border: '1px solid rgba(255,255,255,0.08)' }}
        onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = '#e8eeff'; }}
        onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = '#2e3a5e'; }}>
        <X className="w-6 h-6" />
      </button>

      <p className="text-sm tracking-[8px] uppercase mb-3 font-semibold relative z-10" style={{ color: '#2e3a5e' }}>{time}</p>
      <p className="pnl-label mb-4">TOTAL P&L</p>
      <div className="pnl-value" style={{
        color: isPositive ? '#34d399' : '#fb7185',
        textShadow: isPositive
          ? '0 0 80px rgba(16,185,129,0.5), 0 0 160px rgba(16,185,129,0.2)'
          : '0 0 80px rgba(244,63,94,0.5),  0 0 160px rgba(244,63,94,0.2)',
      }}>
        ₹{pnlFmt(pnl)}
      </div>

      <div className="flex gap-16 mt-12 text-center relative z-10">
        {[
          { label: "Win Rate", value: winRate,    color: '#67e8f9', glow: 'rgba(6,182,212,0.4)' },
          { label: "Trades",   value: String(trades), color: '#a5b4fc', glow: 'rgba(99,102,241,0.4)' },
          { label: "NIFTY",    value: price ? price.toLocaleString("en-IN", { maximumFractionDigits: 1 }) : "--", color: '#fbbf24', glow: 'rgba(251,191,36,0.4)' },
          { label: "Regime",   value: regime,     color: regime?.includes("BULL") ? '#34d399' : regime?.includes("BEAR") ? '#fb7185' : '#fbbf24', glow: 'rgba(6,182,212,0.3)' },
        ].map(({ label, value, color, glow }) => (
          <div key={label}>
            <p className="text-xs tracking-widest uppercase mb-2 font-semibold" style={{ color: '#2e3a5e' }}>{label}</p>
            <p className="text-2xl font-bold" style={{ color, textShadow: `0 0 16px ${glow}` }}>{value}</p>
          </div>
        ))}
      </div>
      <p className="mt-8 text-xs tracking-widest font-semibold uppercase relative z-10" style={{ color: '#2e3a5e' }}>Press Esc to close</p>
    </div>
  );
}
