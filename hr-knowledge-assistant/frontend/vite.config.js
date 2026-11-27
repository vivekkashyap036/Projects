import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /api/* is proxied to FastAPI so the browser sees one origin (no CORS issues in dev).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://localhost:8000", rewrite: (p) => p.replace(/^\/api/, "") } },
  },
});
