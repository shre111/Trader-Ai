"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Lightbulb, Wallet, Filter, LineChart, Settings } from "lucide-react";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/ideas", label: "Recommendations", icon: Lightbulb },
  { href: "/portfolio", label: "Portfolio", icon: Wallet },
  { href: "/screener", label: "Screener", icon: Filter },
  { href: "/backtest", label: "Backtest", icon: LineChart },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const path = usePathname();
  return (
    <aside style={{ width: 244, background: "#fff", borderRight: "1px solid var(--border)", padding: "22px 16px", position: "sticky", top: 0, height: "100vh", flexShrink: 0 }}>
      <div style={{ fontWeight: 700, fontSize: 19, padding: "0 10px 20px", display: "flex", alignItems: "center", gap: 9 }}>
        <span style={{ width: 28, height: 28, borderRadius: 8, background: "var(--primary)", color: "#fff", display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 700 }}>IQ</span>
        InvestIQ
      </div>
      <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = href === "/" ? path === "/" : path.startsWith(href);
          return (
            <Link key={href} href={href} style={{
              display: "flex", alignItems: "center", gap: 11, padding: "9px 12px", borderRadius: 10, fontWeight: 500, fontSize: 14,
              background: active ? "var(--primary-soft)" : "transparent", color: active ? "var(--primary)" : "var(--text)",
            }}>
              <Icon size={18} /> {label}
            </Link>
          );
        })}
      </nav>
      <div style={{ position: "absolute", bottom: 18, left: 16, right: 16, fontSize: 11, lineHeight: 1.5 }} className="muted">
        Paper / educational use.<br />Not investment advice.
      </div>
    </aside>
  );
}
