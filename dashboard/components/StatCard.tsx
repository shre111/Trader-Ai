"use client";

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  color?: "green" | "red" | "yellow" | "blue" | "purple" | "default";
  pulse?: boolean;
}

const colorMap: Record<string, { text: string; glow: string; grad: string; top: string }> = {
  green:   { text: "#10b981", glow: "rgba(16,185,129,0.12)",  grad: "#10b981, #06b6d4", top: "rgba(16,185,129,0.6)"  },
  red:     { text: "#f43f5e", glow: "rgba(244,63,94,0.12)",   grad: "#f43f5e, #8b5cf6", top: "rgba(244,63,94,0.6)"   },
  yellow:  { text: "#f59e0b", glow: "rgba(245,158,11,0.12)",  grad: "#f59e0b, #f97316", top: "rgba(245,158,11,0.6)"  },
  blue:    { text: "#06b6d4", glow: "rgba(6,182,212,0.12)",   grad: "#06b6d4, #6366f1", top: "rgba(6,182,212,0.6)"   },
  purple:  { text: "#8b5cf6", glow: "rgba(139,92,246,0.12)",  grad: "#8b5cf6, #06b6d4", top: "rgba(139,92,246,0.6)"  },
  default: { text: "#a5b4fc", glow: "rgba(99,102,241,0.08)",  grad: "#6366f1, #06b6d4", top: "rgba(99,102,241,0.35)" },
};

export default function StatCard({ label, value, sub, color = "default", pulse }: StatCardProps) {
  const c = colorMap[color];
  return (
    <div
      className="p-4 relative overflow-hidden card-lift"
      style={{
        background: 'rgba(8,14,40,0.8)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: '1px solid rgba(255,255,255,0.07)',
        borderTop: `2px solid ${c.top}`,
        borderRadius: '14px',
        boxShadow: `0 4px 24px rgba(0,0,0,0.35), inset 0 0 40px ${c.glow}, inset 0 1px 0 rgba(255,255,255,0.05)`,
      }}
    >
      {/* Inner glow orb */}
      <div style={{
        position: 'absolute', top: -20, right: -20,
        width: 80, height: 80, borderRadius: '50%',
        background: `radial-gradient(circle, ${c.glow}, transparent 70%)`,
        pointerEvents: 'none',
        filter: 'blur(12px)',
      }} />

      <p className="text-[11px] font-semibold mb-2 relative uppercase tracking-wider" style={{ color: '#3d4f6e', letterSpacing: '0.06em' }}>
        {label}
      </p>
      <div className="text-2xl font-bold flex items-center gap-2 relative value-appear" style={{
        color: c.text,
        letterSpacing: '-0.02em',
        textShadow: `0 0 20px ${c.glow}`,
      }}>
        {pulse && (
          <span className="w-2 h-2 t-pulse flex-shrink-0" style={{
            background: c.text, borderRadius: '50%',
            boxShadow: `0 0 8px ${c.text}`,
          }} />
        )}
        {value}
      </div>
      {sub && (
        <p className="text-[10px] mt-1.5 font-medium relative" style={{ color: '#2e3a5e' }}>{sub}</p>
      )}
    </div>
  );
}
