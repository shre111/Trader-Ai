import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "InvestIQ — AI Investing Advisor",
  description: "AI mutual-fund + equity investing advisor (paper / educational).",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div style={{ display: "flex", minHeight: "100vh" }}>
          <Sidebar />
          <main style={{ flex: 1, minWidth: 0 }}>
            <div style={{ maxWidth: 1240, margin: "0 auto", padding: "28px 32px" }}>{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
