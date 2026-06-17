// InvestIQ API client. Paths are relative — next.config rewrites /api/* → :5055.

export type RiskLevel = "conservative" | "balanced" | "aggressive";

export interface Recommendation {
  symbol: string; name: string; category: string; sec_type: string;
  action: "BUY" | "HOLD" | "SELL";
  final_score: number; ml_prob: number; factor_score: number;
  risk_score: number; momentum_score: number; rationale: string;
  volatility?: number; sharpe?: number; ret_1y?: number;
}
export interface Holding {
  symbol: string; name?: string; units: number; avg_cost: number;
  price: number; value: number; pnl: number; pnl_pct: number; weight: number;
}
export interface PortfolioSummary {
  total_value: number; invested: number; cash: number;
  pnl: number; pnl_pct: number; n_holdings: number;
}
export interface MarketOverview {
  benchmark: string; last: number | null;
  change_1d: number | null; change_1m: number | null;
  breadth: Record<string, number>;
}
export interface EquityPoint { date: string; strategy: number; benchmark: number; }
export interface BacktestResp { risk: string; metrics: Record<string, number>; equity_curve: EquityPoint[]; }
export interface Security { symbol: string; name: string; sec_type: string; category: string; fund_house?: string; benchmark?: string; }

async function fetchJSON<T>(path: string): Promise<T> {
  const r = await fetch(path, { cache: "no-store" });
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}
async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(path, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  return r.json();
}

export const api = {
  health: () => fetchJSON<{ status: string; model_loaded: boolean; counts: Record<string, number> }>("/api/health"),
  profiles: () => fetchJSON<Record<string, unknown>[]>("/api/risk/profiles"),
  securities: () => fetchJSON<Security[]>("/api/securities"),
  recommendations: (risk: RiskLevel) => fetchJSON<Recommendation[]>(`/api/recommendations?risk=${risk}`),
  screener: (risk: RiskLevel, params: Record<string, string> = {}) =>
    fetchJSON<Recommendation[]>(`/api/screener?risk=${risk}&${new URLSearchParams(params)}`),
  security: (sym: string) => fetchJSON<Record<string, any>>(`/api/security/${encodeURIComponent(sym)}`),
  portfolio: () => fetchJSON<{ summary: PortfolioSummary; holdings: Holding[] }>("/api/portfolio"),
  portfolioHistory: () => fetchJSON<{ date: string; total_value: number; pnl: number }[]>("/api/portfolio/history"),
  market: () => fetchJSON<MarketOverview>("/api/market/overview"),
  backtest: (risk: RiskLevel) => fetchJSON<BacktestResp>(`/api/backtest?risk=${risk}`),
  buy: (symbol: string, amount: number) => postJSON("/api/portfolio/buy", { symbol, amount }),
  sell: (symbol: string, fraction: number) => postJSON("/api/portfolio/sell", { symbol, fraction }),
  rebalance: (risk: RiskLevel) => postJSON("/api/portfolio/rebalance", { risk }),
};

export const inr = (n: number | null | undefined) =>
  n == null ? "—" : "₹" + Math.round(n).toLocaleString("en-IN");
export const pct = (n: number | null | undefined, d = 1) =>
  n == null ? "—" : (n >= 0 ? "+" : "") + (n * 100).toFixed(d) + "%";
export const signClass = (n: number | null | undefined) => (n == null ? "" : n >= 0 ? "pos" : "neg");
