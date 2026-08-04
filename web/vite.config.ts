/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { VitePWA } from "vite-plugin-pwa";
import { fileURLToPath } from 'node:url';

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["pwa-icon.svg"],
      // NOTE: offline caching + push notifications are implemented in
      // public/sw.js (NetworkFirst for /api/ reads and navigations,
      // cache-first for static assets). No workbox runtimeCaching here to
      // avoid conflicting with the custom service worker.
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
  preview: {
    port: 5185,
    proxy: {
      "/api": { target: "http://127.0.0.1:8723", changeOrigin: true },
    },
  },
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    css: false,
    exclude: ["**/e2e/**", "**/node_modules/**"],
  },
});
