"use client";
import type { RiskProfile, RiskLevel } from "@/lib/api";

const colors: Record<RiskLevel, { text: string; bg: string; border: string; glow: string }> = {
  low:    { text: "#67e8f9", bg: "rgba(6,182,212,0.1)",  border: "rgba(6,182,212,0.3)",  glow: "rgba(6,182,212,0.15)"  },
  medium: { text: "#c4b5fd", bg: "rgba(139,92,246,0.1)", border: "rgba(139,92,246,0.3)", glow: "rgba(139,92,246,0.15)" },
  high:   { text: "#34d399", bg: "rgba(16,185,129,0.1)", border: "rgba(16,185,129,0.3)", glow: "rgba(16,185,129,0.15)" },
};

export default function RiskProfileCard({ level, profile, active, onSelect }: {
  level: RiskLevel; profile: RiskProfile; active: boolean; onSelect: (l: RiskLevel) => void;
}) {
  const c = colors[level];
  return (
    <button onClick={() => onSelect(level)} className="text-left w-full p-4 transition-all card-lift"
      style={{
        background: active ? `rgba(8,14,40,0.9)` : 'rgba(8,12,32,0.7)',
        backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
        border: `1px solid ${active ? c.border : 'rgba(255,255,255,0.06)'}`,
        borderRadius: '14px',
        borderTop: active ? `2px solid ${c.text}` : '1px solid rgba(255,255,255,0.06)',
        boxShadow: active ? `0 4px 24px rgba(0,0,0,0.4), inset 0 0 40px ${c.glow}, 0 0 0 1px ${c.border}` : '0 2px 12px rgba(0,0,0,0.3)',
      }}>
      <div className="text-xs font-bold capitalize mb-3" style={{ color: active ? c.text : '#3d4f6e', textShadow: active ? `0 0 8px ${c.glow}` : 'none' }}>
        {level} — {profile.name}
      </div>
      <div className="grid grid-cols-2 gap-x-5 gap-y-2 text-xs">
        {[
          ["Lot size", profile.base_lot_size], ["Lot mult", `×${profile.lot_multiplier}`],
          ["SL", `${(profile.sl_pct * 100).toFixed(0)}%`], ["Target", `${(profile.tgt_pct * 100).toFixed(0)}%`],
          ["Min score", (profile.score_threshold * 100).toFixed(0) + "%"], ["Max trades", profile.max_trades_day],
          ["Max premium", `₹${profile.max_premium}`], ["Capital/trade", `${(profile.max_capital_per_trade * 100).toFixed(0)}%`],
        ].map(([k, v]) => (
          <div key={String(k)} className="flex justify-between gap-2">
            <span style={{ color: '#3d4f6e' }}>{k}</span>
            <span className="font-semibold" style={{ color: '#a5b4fc' }}>{v}</span>
          </div>
        ))}
      </div>
    </button>
  );
}
