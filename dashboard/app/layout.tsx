import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import FloatingBubbles from "@/components/FloatingBubbles";

export const metadata: Metadata = {
  title: "AI Trader — Nexus",
  description: "NIFTY Options AI Trading System",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen" suppressHydrationWarning style={{ position: 'relative' }}>
        <FloatingBubbles />
        <div style={{ position: 'relative', zIndex: 1 }}>
          <Providers>{children}</Providers>
        </div>
      </body>
    </html>
  );
}
