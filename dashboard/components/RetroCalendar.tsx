"use client";
import { useState, useMemo, useRef, useEffect } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface CalendarDate { day: string; bars: number; ticks?: number; }
const WEEKDAYS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"];

export default function RetroCalendar({ dates, selectedDate, onSelect }: { dates: CalendarDate[]; selectedDate: string; onSelect: (d: string) => void; }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const barMap  = useMemo(() => { const m: Record<string, number> = {}; for (const d of dates) m[d.day] = d.bars; return m; }, [dates]);
  const tickMap = useMemo(() => { const m: Record<string, number> = {}; for (const d of dates) if (d.ticks) m[d.day] = d.ticks; return m; }, [dates]);

  const initial = selectedDate ? new Date(selectedDate + "T00:00:00") : new Date();
  const [viewYear, setViewYear]   = useState(initial.getFullYear());
  const [viewMonth, setViewMonth] = useState(initial.getMonth());

  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", h); return () => document.removeEventListener("mousedown", h);
  }, []);

  const prevMonth = () => { if (viewMonth === 0) { setViewYear(y => y-1); setViewMonth(11); } else setViewMonth(m => m-1); };
  const nextMonth = () => { if (viewMonth === 11) { setViewYear(y => y+1); setViewMonth(0); } else setViewMonth(m => m+1); };

  const cells = useMemo(() => {
    const first = new Date(viewYear, viewMonth, 1);
    let dow = first.getDay() - 1; if (dow < 0) dow = 6;
    const dim = new Date(viewYear, viewMonth + 1, 0).getDate();
    const out: (null | { date: string; day: number; bars: number|null; ticks: number|null })[] = [];
    for (let i = 0; i < dow; i++) out.push(null);
    for (let d = 1; d <= dim; d++) {
      const ds = `${viewYear}-${String(viewMonth+1).padStart(2,"0")}-${String(d).padStart(2,"0")}`;
      out.push({ date: ds, day: d, bars: barMap[ds] ?? null, ticks: tickMap[ds] ?? null });
    }
    return out;
  }, [viewYear, viewMonth, barMap, tickMap]);

  const monthName = new Date(viewYear, viewMonth).toLocaleString("en-US", { month: "long" });

  return (
    <div className="relative" ref={ref}>
      <button onClick={() => setOpen(o => !o)} className="t-btn flex items-center gap-2">
        <span style={{ background: 'linear-gradient(135deg, #a5b4fc, #67e8f9)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text', fontWeight: 700 }}>
          {selectedDate || "Select date"}
        </span>
        {selectedDate && barMap[selectedDate] !== undefined && <span className="text-[10px]" style={{ color: '#2e3a5e' }}>({barMap[selectedDate]} bars)</span>}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 z-50" style={{ background: "rgba(6,10,28,0.97)", backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', border: "1px solid rgba(99,179,237,0.2)", borderRadius: '16px', boxShadow: "0 16px 64px rgba(0,0,0,0.7), 0 0 40px rgba(99,102,241,0.1)", width: 300, overflow: 'hidden' }}>
          <div className="flex items-center justify-between px-4 py-3" style={{ background: "rgba(255,255,255,0.03)", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
            <button onClick={prevMonth} className="p-1.5 transition-all interactive" style={{ color: '#3d4f6e', borderRadius: '8px' }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = '#67e8f9'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = '#3d4f6e'; }}>
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm font-bold" style={{ background: 'linear-gradient(135deg, #a5b4fc, #67e8f9)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>{monthName} {viewYear}</span>
            <button onClick={nextMonth} className="p-1.5 transition-all interactive" style={{ color: '#3d4f6e', borderRadius: '8px' }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = '#67e8f9'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = '#3d4f6e'; }}>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
          <div className="grid grid-cols-7 px-2 pt-2">
            {WEEKDAYS.map(w => <div key={w} className="text-center text-[9px] font-bold py-1" style={{ color: '#2e3a5e', letterSpacing: '0.05em' }}>{w}</div>)}
          </div>
          <div className="grid grid-cols-7 px-2 pb-3 gap-0.5">
            {cells.map((cell, i) => {
              if (!cell) return <div key={`e-${i}`} />;
              const hasData = cell.bars !== null || cell.ticks !== null;
              const hasTicks = cell.ticks !== null && cell.ticks! > 0;
              const isSel = cell.date === selectedDate;
              const isToday = cell.date === new Date().toISOString().slice(0, 10);
              return (
                <button key={cell.date} onClick={() => { if (hasData) { onSelect(cell.date); setOpen(false); } }} disabled={!hasData}
                  className="flex flex-col items-center py-1.5 transition-all"
                  style={{
                    background: isSel ? 'linear-gradient(135deg, rgba(99,102,241,0.4), rgba(6,182,212,0.25))' : hasData ? 'rgba(255,255,255,0.04)' : 'transparent',
                    border: isToday && !isSel ? '1px solid rgba(6,182,212,0.4)' : isSel ? '1px solid rgba(6,182,212,0.5)' : '1px solid transparent',
                    borderRadius: '8px', color: isSel ? '#e8eeff' : hasData ? '#a5b4fc' : '#1a2540',
                    cursor: hasData ? 'pointer' : 'default', opacity: hasData ? 1 : 0.3,
                    boxShadow: isSel ? '0 2px 12px rgba(99,102,241,0.3)' : 'none',
                  }}>
                  <span className="text-xs font-semibold">{cell.day}</span>
                  {hasData && (
                    <div className="flex items-center gap-0.5 mt-0.5">
                      {cell.bars !== null && cell.bars > 0 && <span className="text-[7px] font-bold" style={{ color: isSel ? 'rgba(255,255,255,0.6)' : '#2e3a5e' }}>{cell.bars}</span>}
                      {hasTicks && <span className="inline-block w-1 h-1" style={{ background: isSel ? '#67e8f9' : '#6366f1', borderRadius: '50%', boxShadow: '0 0 4px rgba(99,102,241,0.6)' }} />}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
          <div className="px-3 py-2 flex items-center gap-3 text-[9px] font-semibold" style={{ borderTop: '1px solid rgba(255,255,255,0.05)', color: '#2e3a5e' }}>
            <span className="flex items-center gap-1"><span style={{ width: 8, height: 8, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '3px', display: 'inline-block' }} />Data</span>
            <span className="flex items-center gap-1"><span style={{ width: 6, height: 6, background: '#6366f1', borderRadius: '50%', display: 'inline-block', boxShadow: '0 0 4px rgba(99,102,241,0.6)' }} />Ticks</span>
            <span className="flex items-center gap-1"><span style={{ width: 8, height: 8, background: 'linear-gradient(135deg, #6366f1, #06b6d4)', borderRadius: '3px', display: 'inline-block' }} />Selected</span>
          </div>
        </div>
      )}
    </div>
  );
}
