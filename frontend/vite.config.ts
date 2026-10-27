import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const root = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(root, "src") } },
  server: { host: true, port: 3000, proxy: { "/api": "http://127.0.0.1:8765" } },
  preview: { port: 3000 },
  build: { outDir: "dist", sourcemap: true }
});
