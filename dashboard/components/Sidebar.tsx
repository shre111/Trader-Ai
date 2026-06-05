"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard, TrendingUp, List, BarChart2,
  Settings, Radio, FlaskConical, Brain, Power, Maximize2, Zap,
} from "lucide-react";
import { fetchJSON, postJSON, type LiveState } from "@/lib/api";
import { useTradingMode } from "@/contexts/TradingModeContext";
import { useFullscreenPnl } from "@/app/providers";

const nav = [
  { href: "/",         label: "Dashboard",  icon: LayoutDashboard },
  { href: "/live",     label: "Live",       icon: Radio },
  { href: "/trades",   label: "Trades",     icon: List },
  { href: "/backtest", label: "Backtest",   icon: FlaskConical },
  { href: "/charts",   label: "Charts",     icon: BarChart2 },
  { href: "/ai",       label: "AI Models",  icon: Brain },
  { href: "/settings", label: "Settings",   icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [status, setStatus]     = useState("connecting");
  const [enabled, setEnabled]   = useState(true);
  const [toggling, setToggling] = useState(false);
  const { mode, setMode } = useTradingMode();
  const { show: onFullscreenPnl } = useFullscreenPnl();

  useEffect(() => {
    const poll = () => {
      fetchJSON<LiveState>("/api/state")
        .then(d => { setStatus(d.status); setEnabled(d.scanner_enabled ?? true); })
        .catch(() => setStatus("offline"));
    };
    poll();
    const id = setInterval(poll, 4000);
    return () => clearInterval(id);
  }, []);

  const toggleSystem = async () => {
    setToggling(true);
    try {
      await postJSON(enabled ? "/api/system/stop" : "/api/system/start");
      setEnabled(!enabled);
      setStatus(enabled ? "stopped" : "idle");
    } catch { /* ignore */ }
    setToggling(false);
  };

  const statusColor =
    status === "scanning" ? "#10b981" :
    status === "idle"     ? "#06b6d4" :
    status === "stopped"  ? "#f43f5e" : "#2e3a5e";

  const statusLabel =
    status === "scanning" ? "Scanning" :
    status === "offline"  ? "Offline" :
    status.charAt(0).toUpperCase() + status.slice(1);

  return (
    <aside
      className="w-56 min-h-screen flex flex-col flex-shrink-0"
      style={{
        background: 'rgba(6, 10, 28, 0.92)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        borderRight: '1px solid rgba(255,255,255,0.07)',
        boxShadow: '4px 0 24px rgba(0,0,0,0.35)',
      }}
    >
      {/* ── Brand ─────────────────────────────────────── */}
      <div className="px-5 py-5" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="flex items-center gap-3">
          {/* Logo mark */}
          <div style={{
            width: 36, height: 36,
            background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
            borderRadius: '10px',
            boxShadow: '0 4px 16px rgba(99,102,241,0.5), 0 0 0 1px rgba(6,182,212,0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
          }}>
            <Zap className="w-4 h-4 text-white" />
          </div>
          <div>
            <div className="font-bold text-sm" style={{
              background: 'linear-gradient(135deg, #a5b4fc, #67e8f9)',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
            }}>
              AI Trader
            </div>
            <div className="text-[10px] font-semibold tracking-widest" style={{ color: '#2e3a5e' }}>NEXUS</div>
          </div>
        </div>
      </div>

      {/* ── Navigation ─────────────────────────────────── */}
      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-3 px-3 py-2.5 text-sm font-medium transition-all relative group"
              style={{
                background: active
                  ? 'linear-gradient(135deg, rgba(99,102,241,0.18), rgba(6,182,212,0.1))'
                  : 'transparent',
                color: active ? '#a5b4fc' : '#3d4f6e',
                borderRadius: '10px',
                border: active ? '1px solid rgba(99,102,241,0.25)' : '1px solid transparent',
                boxShadow: active ? '0 2px 12px rgba(99,102,241,0.15), inset 0 1px 0 rgba(255,255,255,0.06)' : 'none',
              }}
            >
              <Icon
                className="w-4 h-4 flex-shrink-0 transition-all"
                style={{ color: active ? '#67e8f9' : '#3d4f6e', filter: active ? 'drop-shadow(0 0 4px rgba(6,182,212,0.6))' : 'none' }}
              />
              <span style={{ letterSpacing: '0.01em' }}>{label}</span>
              {active && (
                <div style={{
                  position: 'absolute', right: 0, top: '50%', transform: 'translateY(-50%)',
                  width: 3, height: 20, background: 'linear-gradient(180deg, #6366f1, #06b6d4)',
                  borderRadius: '3px 0 0 3px',
                  boxShadow: '0 0 8px rgba(6,182,212,0.6)',
                }} />
              )}
            </Link>
          );
        })}

        {/* Full P&L */}
        <button
          onClick={onFullscreenPnl}
          className="flex items-center gap-3 px-3 py-2.5 text-sm font-medium w-full text-left mt-2 transition-all"
          style={{ color: '#fbbf24', borderRadius: '10px', border: '1px solid transparent', background: 'transparent' }}
          onMouseEnter={e => {
            const el = e.currentTarget as HTMLButtonElement;
            el.style.background = 'rgba(251,191,36,0.08)';
            el.style.borderColor = 'rgba(251,191,36,0.2)';
          }}
          onMouseLeave={e => {
            const el = e.currentTarget as HTMLButtonElement;
            el.style.background = 'transparent';
            el.style.borderColor = 'transparent';
          }}
        >
          <Maximize2 className="w-4 h-4 flex-shrink-0" style={{ filter: 'drop-shadow(0 0 4px rgba(251,191,36,0.5))' }} />
          Full P&amp;L
          <span className="ml-auto text-[10px] font-semibold px-1.5 py-0.5" style={{
            color: '#4a5568', background: 'rgba(255,255,255,0.05)', borderRadius: '5px', border: '1px solid rgba(255,255,255,0.08)',
          }}>⌘K</span>
        </button>
      </nav>

      {/* ── Mode Toggle ─────────────────────────────────── */}
      <div className="px-3 py-3" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <p className="text-[10px] font-bold uppercase tracking-[0.12em] mb-2 px-1" style={{ color: '#2e3a5e' }}>Mode</p>
        <div className="flex gap-1 p-1" style={{ background: 'rgba(0,0,0,0.4)', borderRadius: '11px', border: '1px solid rgba(255,255,255,0.06)' }}>
          <button
            onClick={() => setMode("test")}
            className="flex-1 py-1.5 text-[11px] font-bold text-center transition-all"
            style={{
              background: mode === "test" ? 'linear-gradient(135deg, rgba(245,158,11,0.25), rgba(249,115,22,0.15))' : 'transparent',
              color: mode === "test" ? '#fbbf24' : '#2e3a5e',
              borderRadius: '8px',
              border: mode === "test" ? '1px solid rgba(251,191,36,0.3)' : '1px solid transparent',
              boxShadow: mode === "test" ? '0 2px 8px rgba(251,191,36,0.15)' : 'none',
            }}
          >
            Test
          </button>
          <button
            onClick={() => setMode("live")}
            className="flex-1 py-1.5 text-[11px] font-bold text-center transition-all"
            style={{
              background: mode === "live" ? 'linear-gradient(135deg, rgba(244,63,94,0.25), rgba(239,68,68,0.15))' : 'transparent',
              color: mode === "live" ? '#fb7185' : '#2e3a5e',
              borderRadius: '8px',
              border: mode === "live" ? '1px solid rgba(251,113,133,0.3)' : '1px solid transparent',
              boxShadow: mode === "live" ? '0 2px 8px rgba(251,113,133,0.15)' : 'none',
            }}
          >
            Live
          </button>
        </div>
        {mode === "live" && (
          <p className="text-[10px] mt-2 px-1 font-semibold" style={{ color: '#fb7185' }}>
            ⚠ Real Zerodha executions
          </p>
        )}
      </div>

      {/* ── System Control ─────────────────────────────── */}
      <div className="px-3 py-3 space-y-2" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <button
          onClick={toggleSystem}
          disabled={toggling}
          className="flex items-center justify-center gap-2 w-full py-2.5 text-[12px] font-bold transition-all disabled:opacity-50"
          style={{
            background: enabled
              ? 'linear-gradient(135deg, rgba(244,63,94,0.18), rgba(239,68,68,0.1))'
              : 'linear-gradient(135deg, rgba(16,185,129,0.18), rgba(5,150,105,0.1))',
            border: `1px solid ${enabled ? 'rgba(244,63,94,0.3)' : 'rgba(16,185,129,0.3)'}`,
            color: enabled ? '#fb7185' : '#34d399',
            borderRadius: '10px',
            boxShadow: enabled ? '0 2px 12px rgba(244,63,94,0.1)' : '0 2px 12px rgba(16,185,129,0.1)',
          }}
        >
          <Power className="w-3.5 h-3.5" style={{ filter: `drop-shadow(0 0 4px ${enabled ? 'rgba(251,113,133,0.6)' : 'rgba(52,211,153,0.6)'})`}} />
          {toggling ? "..." : enabled ? "Stop System" : "Start System"}
        </button>

        {/* Status pill */}
        <div className="flex items-center gap-2 px-3 py-2"
          style={{ background: `${statusColor}12`, border: `1px solid ${statusColor}30`, borderRadius: '10px' }}>
          <span className="w-2 h-2 flex-shrink-0" style={{
            background: statusColor, borderRadius: '50%',
            boxShadow: `0 0 8px ${statusColor}`,
            animation: status === "scanning" ? 't-pulse 2s ease-in-out infinite' : 'none',
          }} />
          <span className="text-[11px] font-semibold" style={{ color: statusColor }}>{statusLabel}</span>
        </div>
      </div>
    </aside>
  );
}
