import type { NextConfig } from "next";

const backendApiUrl = process.env.BACKEND_API_URL?.replace(/\/+$/, "");

const nextConfig: NextConfig = {
  async rewrites() {
    if (!backendApiUrl) return [];

    return [{
      source: "/api/backend/:path*",
      destination: `${backendApiUrl}/:path*`,
    }];
  },
};

export default nextConfig;
