import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Standard Vite + React setup. No proxy is configured because the backend
// (api.py) enables permissive CORS for local development instead; see
// src/api.js for how the API base URL is resolved.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
