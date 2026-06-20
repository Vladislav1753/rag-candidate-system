import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit a self-contained server bundle for a minimal Docker runtime image.
  // The browser talks to a same-origin /api/* path that a runtime Route Handler
  // (src/app/api/[...path]/route.ts) forwards to the FastAPI backend, reading
  // BACKEND_URL live. A next.config rewrite can't be used here: its destination
  // is baked in at build time, so the compose BACKEND_URL would be ignored.
  output: "standalone",
};

export default nextConfig;
