"use client";

import { useEffect, useState, useCallback } from "react";
import Sidebar from "@/components/Sidebar";
import StatCard from "@/components/StatCard";
import EquityChart from "@/components/EquityChart";
import TradeTable from "@/components/TradeTable";
import PnlBarChart from "@/components/PnlBarChart";
import { fetchJSON, type BacktestResults, type LiveState, type EquityCurvePoint } from "@/lib/api";
import { RefreshCw } from "lucide-react";

const pnlFmt = (v: number) => `₹${v >= 0 ? "+" : ""}${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
const riskColors = { low: "#67e8f9", medium: "#c4b5fd", high: "#34d399" };
const riskBg     = { low: "rgba(6,182,212,0.1)", medium: "rgba(139,92,246,0.1)", high: "rgba(16,185,129,0.1)" };
const riskBorder = { low: "rgba(6,182,212,0.3)", medium: "rgba(139,92,246,0.3)", high: "rgba(16,185,129,0.3)" };

export default function Home() {
  const [live, setLive]           = useState<LiveState | null>(null);
  const [results, setResults]     = useState<BacktestResults>({});
  const [curves, setCurves]       = useState<Record<string, EquityCurvePoint[]>>({});
  const [activeRisk, setActiveRisk] = useState<"low" | "medium" | "high">("high");
  const [loading, setLoading]     = useState(true);
  const [lastRefresh, setLastRefresh] = useState("--");

  const load = useCallback(async () => {
    try {
      const [liveData, backtestData, curveData] = await Promise.all([
        fetchJSON<LiveState>("/api/state").catch(() => null),
        fetchJSON<BacktestResults>("/api/backtest/results").catch(() => ({})),
        fetchJSON<Record<string, EquityCurvePoint[]>>("/api/equity/curve").catch(() => ({})),
      ]);
      if (liveData) setLive(liveData);
      setResults(backtestData);
      setCurves(curveData);
      setLastRefresh(new Date().toLocaleTimeString("en-IN"));
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); const id = setInterval(load, 5000); return () => clearInterval(id); }, [load]);

  const p = results[activeRisk];

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col min-h-screen overflow-hidden">

        {/* ── Ticker Bar ─────────────────────────────────── */}
        <div className="ticker-bar flex items-center gap-5 px-5 py-3 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 flex-shrink-0" style={{
              background: live?.status === "scanning" ? "#10b981" : live?.status === "idle" ? "#06b6d4" : "#2e3a5e",
              borderRadius: '50%',
              boxShadow: live?.status === "scanning" ? '0 0 8px #10b981, 0 0 16px rgba(16,185,129,0.4)' : live?.status === "idle" ? '0 0 8px #06b6d4' : 'none',
              animation: live?.status === "scanning" ? 't-pulse 2s ease-in-out infinite' : 'none',
            }} />
            <span className="text-xs font-semibold capitalize" style={{ color: '#3d4f6e' }}>{live?.status ?? "connecting"}</span>
          </div>
          <div className="w-px h-4" style={{ background: 'rgba(255,255,255,0.08)' }} />
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold uppercase tracking-wider" style={{ color: '#2e3a5e' }}>NIFTY</span>
            <span className="text-sm font-bold" style={{ color: '#fbbf24', textShadow: '0 0 12px rgba(251,191,36,0.5)' }}>
              {live?.last_price ? `₹${live.last_price.toLocaleString("en-IN", { maximumFractionDigits: 1 })}` : "--"}
            </span>
          </div>
          <div className="w-px h-4" style={{ background: 'rgba(255,255,255,0.08)' }} />
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold" style={{ color: '#2e3a5e' }}>Regime</span>
            <span className="text-xs font-bold px-2.5 py-0.5" style={{
              color: live?.regime?.includes("BULL") ? '#34d399' : live?.regime?.includes("BEAR") ? '#fb7185' : '#fbbf24',
              background: live?.regime?.includes("BULL") ? 'rgba(16,185,129,0.1)' : live?.regime?.includes("BEAR") ? 'rgba(244,63,94,0.1)' : 'rgba(245,158,11,0.1)',
              border: `1px solid ${live?.regime?.includes("BULL") ? 'rgba(16,185,129,0.3)' : live?.regime?.includes("BEAR") ? 'rgba(244,63,94,0.3)' : 'rgba(245,158,11,0.3)'}`,
              borderRadius: '8px', textShadow: '0 0 6px rgba(255,255,255,0.2)',
            }}>{live?.regime ?? "--"}</span>
          </div>
          <div className="w-px h-4" style={{ background: 'rgba(255,255,255,0.08)' }} />
          <div className="flex items-center gap-5">
            {[["Scans", live?.scan_count ?? 0, '#3d4f6e'], ["Signals", live?.signals_checked ?? 0, '#3d4f6e'], ["Trades", live?.trades_today ?? 0, '#67e8f9']].map(([l, v, c]) => (
              <div key={String(l)} className="flex items-center gap-1.5">
                <span className="text-[11px] font-medium" style={{ color: '#2e3a5e' }}>{l}</span>
                <span className="text-xs font-bold" style={{ color: c as string, textShadow: c === '#67e8f9' ? '0 0 8px rgba(103,232,249,0.4)' : 'none' }}>{v}</span>
              </div>
            ))}
          </div>
          <div className="ml-auto flex items-center gap-3">
            <span className="text-[11px] font-medium" style={{ color: '#2e3a5e' }}>{lastRefresh}</span>
            <button onClick={load} className="t-btn flex items-center gap-1.5 text-xs">
              <RefreshCw className="w-3 h-3" /> Refresh
            </button>
          </div>
        </div>

        {/* ── Main ─────────────────────────────────────── */}
        <main className="flex-1 p-5 overflow-y-auto">

          {/* Risk tabs */}
          <div className="flex gap-2 mb-6">
            {(["low", "medium", "high"] as const).map(r => (
              <button key={r} onClick={() => setActiveRisk(r)} className="px-5 py-2 text-sm font-bold capitalize transition-all interactive"
                style={{
                  background: activeRisk === r ? riskBg[r] : 'rgba(255,255,255,0.03)',
                  color: activeRisk === r ? riskColors[r] : '#3d4f6e',
                  border: `1px solid ${activeRisk === r ? riskBorder[r] : 'rgba(255,255,255,0.07)'}`,
                  borderRadius: '10px',
                  boxShadow: activeRisk === r ? `0 4px 16px ${riskBg[r]}, inset 0 1px 0 rgba(255,255,255,0.07)` : 'none',
                  textShadow: activeRisk === r ? `0 0 8px ${riskColors[r]}88` : 'none',
                }}>
                {r} Risk
              </button>
            ))}
          </div>

          {/* KPI cards */}
          {loading ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
              {[...Array(8)].map((_, i) => <div key={i} className="h-24 animate-pulse" style={{ borderRadius: '14px', border: '1px solid rgba(255,255,255,0.05)' }} />)}
            </div>
          ) : p ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
              <StatCard label="Total P&L"     value={pnlFmt(p.pnl)}    color={p.pnl >= 0 ? "green" : "red"} />
              <StatCard label="Win Rate"      value={`${p.win_rate}%`} color={p.win_rate >= 55 ? "green" : p.win_rate >= 45 ? "yellow" : "red"} />
              <StatCard label="Total Trades"  value={p.trades}         sub={`${(p.pnl / Math.max(p.trades, 1)).toFixed(0)} avg / trade`} />
              <StatCard label="Risk-Reward"   value={`${p.rr}×`}       color={p.rr >= 1.5 ? "green" : p.rr >= 1.0 ? "yellow" : "red"} />
              <StatCard label="Avg Winner"    value={pnlFmt(p.avg_win)} color="green" />
              <StatCard label="Avg Loser"     value={pnlFmt(p.avg_loss)} color="red" />
              <StatCard label="Max Drawdown"  value={pnlFmt(p.max_dd)} color="red" />
              <StatCard label="Profit Factor" value={p.avg_loss !== 0 ? (p.avg_win / Math.abs(p.avg_loss)).toFixed(2) : "∞"} color="blue" />
            </div>
          ) : (
            <div className="p-6 mb-6 text-sm text-center t-panel" style={{ color: '#3d4f6e' }}>
              No backtest data for <span style={{ color: riskColors[activeRisk], fontWeight: 700 }}>{activeRisk}</span> risk. Run{' '}
              <code style={{ color: '#67e8f9', background: 'rgba(6,182,212,0.08)', padding: '2px 6px', borderRadius: '5px' }}>
                python scripts/tick_replay_backtest.py --risk {activeRisk}
              </code>
            </div>
          )}

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
            <div className="t-panel p-5">
              <h3 className="text-sm font-bold mb-4 gradient-text">Equity Curves</h3>
              <EquityChart curves={curves} selected="all" />
            </div>
            <div className="t-panel p-5">
              <h3 className="text-sm font-bold mb-4" style={{ color: '#e8eeff' }}>
                Per-Trade P&amp;L — <span style={{ color: riskColors[activeRisk], textShadow: `0 0 8px ${riskColors[activeRisk]}66` }}>{activeRisk}</span>
              </h3>
              {p?.trade_list ? <PnlBarChart trades={p.trade_list} /> : <div className="h-48 flex items-center justify-center text-sm" style={{ color: '#2e3a5e' }}>No data</div>}
            </div>
          </div>

          {/* Risk comparison */}
          <div className="t-panel p-5 mb-6">
            <h3 className="text-sm font-bold mb-4 gradient-text">Risk Profile Comparison</h3>
            <div className="overflow-x-auto">
              <table>
                <thead><tr>{["Profile","Trades","Total P&L","Win Rate","R:R","Avg / Trade","Max DD"].map(h => <th key={h}>{h}</th>)}</tr></thead>
                <tbody>
                  {(["low","medium","high"] as const).map(r => {
                    const rp = results[r]; if (!rp) return null;
                    return (
                      <tr key={r} style={{ background: activeRisk === r ? 'rgba(99,102,241,0.04)' : undefined }}>
                        <td><span className="font-bold capitalize px-2.5 py-1 text-xs" style={{ color: riskColors[r], background: riskBg[r], border: `1px solid ${riskBorder[r]}`, borderRadius: '8px', boxShadow: `0 0 8px ${riskBg[r]}`, textShadow: `0 0 6px ${riskColors[r]}88` }}>{r}</span></td>
                        <td style={{ color: '#a5b4fc' }}>{rp.trades}</td>
                        <td style={{ color: rp.pnl >= 0 ? '#34d399' : '#fb7185', fontWeight: 700, textShadow: `0 0 8px ${rp.pnl >= 0 ? 'rgba(52,211,153,0.3)' : 'rgba(251,113,133,0.3)'}` }}>{pnlFmt(rp.pnl)}</td>
                        <td style={{ color: '#a5b4fc' }}>{rp.win_rate}%</td>
                        <td style={{ color: '#a5b4fc' }}>{rp.rr}×</td>
                        <td style={{ color: '#a5b4fc' }}>{pnlFmt(rp.pnl / Math.max(rp.trades, 1))}</td>
                        <td style={{ color: '#fb7185', textShadow: '0 0 6px rgba(251,113,133,0.3)' }}>{pnlFmt(rp.max_dd)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recent trades */}
          <div className="t-panel p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold" style={{ color: '#e8eeff' }}>
                Recent Trades — <span style={{ color: riskColors[activeRisk], textShadow: `0 0 8px ${riskColors[activeRisk]}55` }}>{activeRisk}</span>
              </h3>
              <a href="/trades" className="text-xs font-bold transition-all" style={{ color: '#67e8f9', textShadow: '0 0 8px rgba(6,182,212,0.4)' }}
                onMouseEnter={e => { (e.currentTarget as HTMLAnchorElement).style.textShadow = '0 0 16px rgba(6,182,212,0.7)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLAnchorElement).style.textShadow = '0 0 8px rgba(6,182,212,0.4)'; }}>
                View all →
              </a>
            </div>
            {p?.trade_list ? <TradeTable trades={p.trade_list} maxRows={10} /> : <p className="text-sm text-center py-8" style={{ color: '#2e3a5e' }}>No trades</p>}
          </div>
        </main>
      </div>
    </div>
  );
}
