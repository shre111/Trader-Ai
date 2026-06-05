"use client";

import { useEffect, useState, useCallback } from "react";
import Sidebar from "@/components/Sidebar";
import { fetchJSON, type RLStatus } from "@/lib/api";
import { RefreshCw } from "lucide-react";

export default function AIPage() {
  const [rl, setRl] = useState<RLStatus>({});
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchJSON<RLStatus>("/api/rl/status").catch(() => ({}));
      setRl(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-5 overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h1 className="text-sm font-bold uppercase tracking-wider" style={{ color: '#10b981' }}>AI Models</h1>
            <p className="text-[10px] mt-0.5" style={{ color: '#2e3a5e' }}>ML MODELS, RL AGENTS & TRAINING STATUS</p>
          </div>
          <button onClick={load} className="t-btn flex items-center gap-1.5">
            <RefreshCw className="w-3 h-3" /> REFRESH
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-[1px] mb-4">
          {/* Tabular RL agent */}
          <div className="t-panel p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-[12px] font-bold uppercase tracking-wider" style={{ color: '#06b6d4' }}>Tabular Q-Learning</h3>
                <p className="text-[10px] mt-0.5" style={{ color: '#2e3a5e' }}>models/saved/rl_exit_agent.pkl</p>
              </div>
              <span className="w-[6px] h-[6px]" style={{ background: rl.tabular ? '#10b981' : '#f43f5e' }} />
            </div>
            {rl.tabular ? (
              <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-[11px]">
                {[
                  ["States",    rl.tabular.states?.toLocaleString() ?? "--"],
                  ["Episodes",  rl.tabular.episodes?.toLocaleString() ?? "--"],
                  ["Actions",   "HOLD / EXIT / TIGHTEN"],
                  ["Type",      "Tabular Q-Table"],
                ].map(([k, v]) => (
                  <div key={String(k)}>
                    <span style={{ color: '#5e7299' }}>{k}</span>
                    <p className="font-semibold" style={{ color: '#e8eeff' }}>{v}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[11px]" style={{ color: '#2e3a5e' }}>
                NOT LOADED — <code style={{ color: '#06b6d4' }}>python scripts/train_rl_exit.py --epochs 10</code>
              </p>
            )}
            <div className="mt-4 pt-4" style={{ borderTop: '1px solid rgba(255,255,255,0.07)' }}>
              <p className="text-[10px]" style={{ color: '#5e7299' }}>LAST KNOWN RESULTS:</p>
              <p className="text-[10px] mt-1">Trained on <span style={{ color: '#e8eeff' }}>247,234 episodes</span> · 124 days · 11,606 states</p>
              <p className="text-[10px]">Eval: <span style={{ color: '#10b981' }}>88.1% WR</span>, <span style={{ color: '#10b981' }}>+1.01% avg P&L</span></p>
              <p className="text-[10px]">Backtest: <span style={{ color: '#10b981' }}>100% RL_EXIT WR</span></p>
            </div>
          </div>

          {/* DQN agent */}
          <div className="t-panel p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-[12px] font-bold uppercase tracking-wider" style={{ color: '#8b5cf6' }}>DQN Agent</h3>
                <p className="text-[10px] mt-0.5" style={{ color: '#2e3a5e' }}>models/saved/dqn_exit_agent.pt</p>
              </div>
              <span className="w-[6px] h-[6px]" style={{ background: rl.dqn ? '#10b981' : '#f43f5e' }} />
            </div>
            {rl.dqn ? (
              <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-[11px]">
                {[
                  ["Episodes",        rl.dqn.episodes?.toLocaleString() ?? "--"],
                  ["Training Steps",  rl.dqn.training_steps?.toLocaleString() ?? "--"],
                  ["Epsilon",         rl.dqn.epsilon?.toFixed(4) ?? "--"],
                  ["Parameters",      rl.dqn.params?.toLocaleString() ?? "--"],
                  ["Architecture",    "64→64→32 LayerNorm"],
                  ["Algorithm",       "Double DQN + Huber"],
                ].map(([k, v]) => (
                  <div key={String(k)}>
                    <span style={{ color: '#5e7299' }}>{k}</span>
                    <p className="font-semibold" style={{ color: '#e8eeff' }}>{v}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[11px]" style={{ color: '#2e3a5e' }}>
                NOT LOADED — <code style={{ color: '#06b6d4' }}>python scripts/train_dqn_exit.py --epochs 10</code>
              </p>
            )}
            <div className="mt-4 pt-4" style={{ borderTop: '1px solid rgba(255,255,255,0.07)' }}>
              <p className="text-[10px]" style={{ color: '#5e7299' }}>ADVANTAGES OVER TABULAR:</p>
              <div className="text-[10px] mt-1 space-y-0.5">
                <p><span style={{ color: '#e8eeff' }}>Continuous states</span> <span style={{ color: '#2e3a5e' }}>— no discretization</span></p>
                <p><span style={{ color: '#e8eeff' }}>Double DQN</span> <span style={{ color: '#2e3a5e' }}>— reduces overestimation</span></p>
                <p><span style={{ color: '#e8eeff' }}>Replay buffer</span> <span style={{ color: '#2e3a5e' }}>— 50K stable training</span></p>
                <p><span style={{ color: '#e8eeff' }}>Generalizes</span> <span style={{ color: '#2e3a5e' }}>— unseen markets</span></p>
              </div>
            </div>
          </div>
        </div>

        {/* System models grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-[1px] mb-4">
          {[
            {
              title: "Macro ML Model",
              path: "models/saved/macro_model.pkl",
              desc: "LightGBM — 46K bars — AUC 0.98",
              details: ["80+ technical indicators", "Bull/Bear probability output", "Sep 2025–Mar 2026 training"],
              color: "#06b6d4",
            },
            {
              title: "Strategy Models",
              path: "models/saved/strategy_*.pkl",
              desc: "Per-strategy LightGBM classifiers",
              details: ["Breakout, Reversal, Momentum", "Mar 10-20 tick data training", "Strategy success probability"],
              color: "#8b5cf6",
            },
            {
              title: "Vol Surface",
              path: "strategy/vol_surface.py",
              desc: "IV-based strike selection",
              details: ["IV edge 30%, moneyness 25%", "OI liquidity 20%, theta 10%", "Optimal strike scoring"],
              color: "#10b981",
            },
          ].map(m => (
            <div key={m.title} className="t-panel p-4">
              <h3 className="text-[12px] font-bold uppercase tracking-wider mb-1" style={{ color: m.color }}>{m.title}</h3>
              <p className="text-[10px] mb-2" style={{ color: '#2e3a5e' }}>{m.path}</p>
              <p className="text-[11px] mb-3" style={{ color: '#e8eeff' }}>{m.desc}</p>
              <div className="space-y-0.5">
                {m.details.map(d => (
                  <p key={d} className="text-[10px]" style={{ color: '#5e7299' }}>› {d}</p>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Kelly position sizer */}
        <div className="t-panel p-5">
          <h3 className="text-[12px] font-bold uppercase tracking-wider mb-3" style={{ color: '#10b981' }}>Kelly Criterion Sizer</h3>
          <p className="text-[11px] mb-3" style={{ color: '#5e7299' }}>
            Capital-aware sizing. Half-Kelly for safety, capped by <code style={{ color: '#06b6d4' }}>max_capital_per_trade</code>.
          </p>
          <div className="p-4 text-[11px]" style={{ background: '#050814', border: '1px solid rgba(10,18,50,0.9)' }}>
            <span style={{ color: '#06b6d4' }}>f*</span> <span style={{ color: '#5e7299' }}>=</span> (p × b − q) / b × <span style={{ color: '#10b981' }}>0.5</span> × regime_mult<br/>
            <span className="text-[10px]" style={{ color: '#2e3a5e' }}>p=win_rate, q=1−p, b=avg_win/avg_loss</span><br/>
            <span className="text-[10px]" style={{ color: '#2e3a5e' }}>Clamped: min 1 lot (65), max 5 lots (325)</span>
          </div>
          <div className="grid grid-cols-3 gap-4 mt-4 text-[11px]">
            {[
              { label: "Initial Capital", value: "₹50,000" },
              { label: "Lot Size", value: "65 units" },
              { label: "Rolling Window", value: "Last 20 trades" },
            ].map(({ label, value }) => (
              <div key={label}>
                <span style={{ color: '#5e7299' }}>{label}</span>
                <p className="font-semibold" style={{ color: '#e8eeff' }}>{value}</p>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
