import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// The backend runs on the same laptop. The browser only ever talks to this server
// (same origin), so no backend CORS change is needed. GET/HEAD and Range headers
// are passed through unchanged by the proxy, which COG tile reading depends on.
const API_TARGET = "http://127.0.0.1:8786";
// Team 2's candidate service is a separate loopback service (contract 1.0.0). Its three routes go to 8770;
// This integrated copy uses the combined reference API on 8767; keep this before the general /api rule.
const CANDIDATE_TARGET = "http://127.0.0.1:8778";
const proxy = {
  "/api/v1/candidates": { target: CANDIDATE_TARGET, changeOrigin: false, secure: false },
  "/api": { target: API_TARGET, changeOrigin: false, secure: false },
};

export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5175, strictPort: true, proxy },
  preview: { host: "127.0.0.1", port: 5175, strictPort: true, proxy },
  build: { target: "es2022", sourcemap: false, chunkSizeWarningLimit: 1200 },
  test: { environment: "node", include: ["src/**/*.test.ts", "src/**/*.test.tsx"] },
});
