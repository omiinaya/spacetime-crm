/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["pwa-icon.svg"],
      manifest: {
        name: "SpacetimeCRM",
        short_name: "CRM",
        description: "Repair shop CRM — customers, tickets, invoices, inventory",
        start_url: "/",
        display: "standalone",
        background_color: "#0a0a0a",
        theme_color: "#3b82f6",
        icons: [
          { src: "/pwa-icon.svg", sizes: "512x512", type: "image/svg+xml" },
        ],
      },
    }),
  ],
  server: {
    port: 5185,
    proxy: {
      "/api": { target: "http://127.0.0.1:8723", changeOrigin: true },
    },
  },
  resolve: {
    alias: { "@": new URL("./src", import.meta.url).pathname },
  },
  test: {
    coverage: {
      provider: "v8",
      thresholds: {
        statements: 20,
        branches: 15,
        functions: 20,
        lines: 20,
      },
    },
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    css: false,
    exclude: ["**/e2e/**", "**/node_modules/**"],
  },
});
