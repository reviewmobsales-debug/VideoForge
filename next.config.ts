import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  basePath: "/VideoForge",
  images: { unoptimized: true },
};

export default nextConfig;
