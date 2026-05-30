"use client";

type Variant = "green" | "red" | "yellow" | "blue" | "purple" | "gray";

const colors: Record<Variant, { border: string; text: string; bg: string; glow: string }> = {
  green:  { border: 'rgba(16,185,129,0.4)',  text: '#34d399', bg: 'rgba(16,185,129,0.1)',  glow: 'rgba(16,185,129,0.25)'  },
  red:    { border: 'rgba(244,63,94,0.4)',   text: '#fb7185', bg: 'rgba(244,63,94,0.1)',   glow: 'rgba(244,63,94,0.25)'   },
  yellow: { border: 'rgba(245,158,11,0.4)',  text: '#fbbf24', bg: 'rgba(245,158,11,0.1)',  glow: 'rgba(245,158,11,0.2)'   },
  blue:   { border: 'rgba(6,182,212,0.4)',   text: '#67e8f9', bg: 'rgba(6,182,212,0.1)',   glow: 'rgba(6,182,212,0.25)'   },
  purple: { border: 'rgba(139,92,246,0.4)',  text: '#c4b5fd', bg: 'rgba(139,92,246,0.1)',  glow: 'rgba(139,92,246,0.25)'  },
  gray:   { border: 'rgba(99,119,160,0.25)', text: '#5e7299', bg: 'rgba(99,119,160,0.08)', glow: 'transparent'            },
};

export default function Badge({ label, variant = "gray" }: { label: string; variant?: Variant }) {
  const c = colors[variant];
  return (
    <span
      className="t-badge"
      style={{
        borderColor: c.border,
        color: c.text,
        background: c.bg,
        boxShadow: c.glow !== 'transparent' ? `0 0 8px ${c.glow}` : 'none',
        textShadow: c.glow !== 'transparent' ? `0 0 8px ${c.glow}` : 'none',
      }}
    >
      {label}
    </span>
  );
}
