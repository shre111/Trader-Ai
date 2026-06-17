import type { NextConfig } from "next";

// Proxy /api/* to the InvestIQ Flask API (port 5055) so the client uses same-origin paths.
const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:5055/api/:path*",
      },
    ];
  },
};

export default nextConfig;
