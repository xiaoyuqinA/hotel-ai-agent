import { defineConfig } from "vite";
import { resolve } from "path";
import { copyFileSync, existsSync, mkdirSync, cpSync, readdirSync } from "fs";

const ROOT = resolve(import.meta.url ? new URL(".", import.meta.url).pathname : ".", ".");
const PUBLIC = resolve(ROOT, "public");
const DIST = resolve(ROOT, "dist");

export default defineConfig({
  build: {
    outDir: DIST,
    emptyOutDir: true,
    rollupOptions: {
      input: {
        contentScript: resolve(ROOT, "src/content-script/index.ts"),
        background: resolve(ROOT, "src/background/service-worker.ts"),
        popup: resolve(ROOT, "src/popup/popup.ts"),
      },
      output: {
        entryFileNames: "[name].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
});

// Use after-build: copy static assets
// Run via package.json script instead
