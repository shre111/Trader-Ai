"use client";

import { useEffect, useRef } from "react";

// ── Bubble config ─────────────────────────────────────────────
const BUBBLES = [
  // [id, size, left%, delay, duration, animation, color1, color2, icon]
  [1,  80,  4, 0,    28, "a", "#6366f1", "#06b6d4", "brain"],
  [2,  45,  9, 4,    22, "b", "#8b5cf6", "#6366f1", null],
  [3,  110, 17, 8,   34, "c", "#06b6d4", "#3b82f6", "chart"],
  [4,  35,  24, 1,   19, "d", "#6366f1", "#8b5cf6", null],
  [5,  65,  30, 12,  26, "a", "#10b981", "#06b6d4", "zap"],
  [6,  90,  38, 5,   31, "b", "#8b5cf6", "#06b6d4", "activity"],
  [7,  40,  44, 18,  21, "c", "#3b82f6", "#6366f1", null],
  [8,  120, 52, 9,   38, "d", "#06b6d4", "#10b981", "bar"],
  [9,  50,  58, 3,   24, "a", "#6366f1", "#8b5cf6", null],
  [10, 75,  65, 15,  29, "b", "#f59e0b", "#f97316", "trend"],
  [11, 30,  71, 7,   18, "c", "#8b5cf6", "#06b6d4", null],
  [12, 95,  78, 11,  35, "d", "#6366f1", "#06b6d4", "brain"],
  [13, 55,  84, 2,   23, "a", "#10b981", "#6366f1", null],
  [14, 140, 91, 16,  42, "b", "#8b5cf6", "#3b82f6", "chart"],
  [15, 38,  96, 6,   20, "c", "#06b6d4", "#8b5cf6", null],
  [16, 68,  14, 20,  27, "d", "#3b82f6", "#06b6d4", "activity"],
  [17, 48,  48, 13,  22, "a", "#6366f1", "#10b981", null],
  [18, 85,  73, 22,  32, "b", "#06b6d4", "#6366f1", "zap"],
  [19, 42,  33, 10,  20, "c", "#8b5cf6", "#f59e0b", null],
  [20, 100, 60, 19,  36, "d", "#6366f1", "#8b5cf6", "bar"],
];

// ── SVG Icon paths ────────────────────────────────────────────
const ICONS: Record<string, JSX.Element> = {
  brain: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"/>
      <path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"/>
      <path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4"/>
      <path d="M17.599 6.5a3 3 0 0 0 .399-1.375"/>
      <path d="M6.003 5.125A3 3 0 0 0 6.401 6.5"/>
      <path d="M3.477 10.896a4 4 0 0 1 .585-.396"/>
      <path d="M19.938 10.5a4 4 0 0 1 .585.396"/>
      <path d="M6 18a4 4 0 0 1-1.967-.516"/>
      <path d="M19.967 17.484A4 4 0 0 1 18 18"/>
    </svg>
  ),
  chart: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10"/>
      <line x1="12" y1="20" x2="12" y2="4"/>
      <line x1="6" y1="20" x2="6" y2="14"/>
      <line x1="2" y1="20" x2="22" y2="20"/>
    </svg>
  ),
  zap: (
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
    </svg>
  ),
  activity: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  ),
  bar: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="4" height="18" rx="1"/>
      <rect x="10" y="8" width="4" height="13" rx="1"/>
      <rect x="17" y="5" width="4" height="16" rx="1"/>
    </svg>
  ),
  trend: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
      <polyline points="17 6 23 6 23 12"/>
    </svg>
  ),
};

// ── Component ─────────────────────────────────────────────────
export default function FloatingBubbles() {
  return (
    <div
      aria-hidden="true"
      style={{
        position: 'fixed',
        inset: 0,
        pointerEvents: 'none',
        overflow: 'hidden',
        zIndex: 0,
      }}
    >
      {BUBBLES.map(([id, size, left, delay, duration, anim, c1, c2, icon]) => {
        const sz   = size as number;
        const iconEl = icon ? ICONS[icon as string] : null;
        const iconSize = Math.round(sz * 0.42);
        const animName = `bubble-rise-${anim as string}`;

        return (
          <div
            key={id as number}
            className="bubble"
            style={{
              width:  sz,
              height: sz,
              left:   `${left as number}%`,
              bottom: `-${sz + 20}px`,
              background: `radial-gradient(circle at 35% 35%, ${c1 as string}22, ${c2 as string}0a 60%, transparent)`,
              border: `1px solid ${c1 as string}30`,
              boxShadow: `0 0 ${sz * 0.4}px ${c1 as string}18, inset 0 0 ${sz * 0.3}px ${c2 as string}10`,
              backdropFilter: 'blur(3px)',
              WebkitBackdropFilter: 'blur(3px)',
              animation: `${animName} ${duration as number}s ${delay as number}s ease-in-out infinite`,
            }}
          >
            {iconEl && (
              <div style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <div style={{
                  width: iconSize,
                  height: iconSize,
                  color: c1 as string,
                  opacity: 0.7,
                  animation: `bubble-inner-glow 3s ease-in-out infinite`,
                  animationDelay: `${(delay as number) * 0.5}s`,
                }}>
                  {iconEl}
                </div>
              </div>
            )}
          </div>
        );
      })}

      {/* Static deep glow orbs in background */}
      <div style={{
        position: 'absolute', top: '15%', left: '10%',
        width: 600, height: 600, borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(99,102,241,0.06) 0%, transparent 70%)',
        filter: 'blur(60px)',
        animation: 'glow-breathe 8s ease-in-out infinite',
        pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute', bottom: '20%', right: '8%',
        width: 500, height: 500, borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(6,182,212,0.07) 0%, transparent 70%)',
        filter: 'blur(60px)',
        animation: 'glow-breathe 10s ease-in-out infinite',
        animationDelay: '4s',
        pointerEvents: 'none',
      }} />
      <div style={{
        position: 'absolute', top: '55%', left: '45%',
        width: 400, height: 400, borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(139,92,246,0.05) 0%, transparent 70%)',
        filter: 'blur(60px)',
        animation: 'glow-breathe 12s ease-in-out infinite',
        animationDelay: '2s',
        pointerEvents: 'none',
      }} />
    </div>
  );
}
