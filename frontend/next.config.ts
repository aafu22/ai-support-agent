import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Give slow LLM replies time to finish before the dev proxy gives up.
  // If your Next.js version rejects this option, delete this line.
  experimental: { proxyTimeout: 120_000 },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_URL ?? "http://127.0.0.1:8000"}/:path*`,
      },
    ];
  },
};

export default nextConfig;