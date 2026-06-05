"use client";
interface RetroDialogProps { open: boolean; onClose: () => void; title: string; message: string; type?: "error" | "warning" | "info"; }

export default function RetroDialog({ open, onClose, title, message, type = "error" }: RetroDialogProps) {
  if (!open) return null;
  const accent = type === "error" ? "#fb7185" : type === "warning" ? "#fbbf24" : "#67e8f9";
  const accentBg = type === "error" ? "rgba(244,63,94,0.08)" : type === "warning" ? "rgba(245,158,11,0.08)" : "rgba(6,182,212,0.08)";
  const accentBorder = type === "error" ? "rgba(244,63,94,0.3)" : type === "warning" ? "rgba(245,158,11,0.3)" : "rgba(6,182,212,0.3)";
  const iconChar = type === "error" ? "✖" : type === "warning" ? "⚠" : "ℹ";
  return (
    <div className="fixed inset-0 z-[9998] flex items-center justify-center" style={{ background: "rgba(0,0,0,0.8)", backdropFilter: 'blur(8px)' }}>
      <div style={{ background: "rgba(8,14,40,0.95)", backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', border: `1px solid ${accentBorder}`, borderRadius: '20px', boxShadow: `0 0 60px ${accent}20, 0 24px 80px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.06)`, overflow: 'hidden', width: '100%', maxWidth: '28rem' }}>
        <div className="flex items-center justify-between px-6 py-4" style={{ background: accentBg, borderBottom: `1px solid ${accentBorder}` }}>
          <div className="flex items-center gap-3">
            <span style={{ color: accent, fontSize: 16, textShadow: `0 0 8px ${accentBorder}` }}>{iconChar}</span>
            <span className="text-sm font-bold" style={{ color: accent }}>{title}</span>
          </div>
          <button onClick={onClose} className="text-xs font-semibold px-2.5 py-1.5 transition-all interactive"
            style={{ color: '#5e7299', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.05)', borderRadius: '8px' }}>✕</button>
        </div>
        <div className="px-6 py-6"><p className="text-sm leading-relaxed" style={{ color: '#a5b4fc', whiteSpace: 'pre-wrap' }}>{message}</p></div>
        <div className="px-6 py-4 flex justify-end" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <button onClick={onClose} className="text-sm font-bold px-6 py-2 transition-all btn-gradient"
            style={{ background: accent === '#fb7185' ? 'linear-gradient(135deg, #f43f5e, #8b5cf6)' : accent === '#fbbf24' ? 'linear-gradient(135deg, #f59e0b, #f97316)' : 'linear-gradient(135deg, #6366f1, #06b6d4)' }}>
            OK
          </button>
        </div>
      </div>
    </div>
  );
}
