import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // The shared filebase is symlinked into workspaces, so two lockfiles appear
  // (one here, one in the workspace root). Pin the tracing root to the app
  // directory so Next.js does not try to walk the host filesystem.
  outputFileTracingRoot: path.resolve(__dirname),
};

export default nextConfig;
