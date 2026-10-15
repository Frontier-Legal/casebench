import path from "node:path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vitest/config"

// The build ships inside the Python package, which serves it (decision 0050). The build of
// casebench-ee names its own extension module and output folder (decision 0058).
const extension = process.env.CASEBENCH_EXTENSION
const outDir = process.env.CASEBENCH_STATIC ?? "../casebench/workbench/static"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: [
      ...(extension ? [{ find: "@/extension", replacement: path.resolve(__dirname, extension) }] : []),
      { find: "@", replacement: path.resolve(__dirname, "./src") },
    ],
  },
  build: {
    outDir: path.resolve(__dirname, outDir),
    emptyOutDir: true,
    // The app is served from this machine, so one bundle loads faster than many.
    chunkSizeWarningLimit: 1000,
  },
  server: {
    proxy: { "/api": "http://127.0.0.1:7462" },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
})
