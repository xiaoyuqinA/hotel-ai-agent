import { defineConfig } from "vite";
import { resolve } from "path";
import { copyFileSync, existsSync, mkdirSync, cpSync } from "fs";

const ROOT = resolve(import.meta.url ? new URL(".", import.meta.url).pathname : ".");
const PUBLIC = resolve(ROOT, "public");
const DIST = resolve(ROOT, "dist");

function copyStaticAssets() {
  return {
    name: "copy-static-assets",
    closeBundle() {
      const manifestSrc = resolve(PUBLIC, "manifest.json");
      const manifestDst = resolve(DIST, "manifest.json");
      if (existsSync(manifestSrc)) copyFileSync(manifestSrc, manifestDst);

      const iconsSrc = resolve(PUBLIC, "icons");
      const iconsDst = resolve(DIST, "icons");
      if (existsSync(iconsSrc)) {
        if (!existsSync(iconsDst)) mkdirSync(iconsDst, { recursive: true });
        cpSync(iconsSrc, iconsDst, { recursive: true });
      }

      const popupHtmlSrc = resolve(ROOT, "src", "popup", "index.html");
      const popupHtmlDst = resolve(DIST, "popup", "index.html");
      if (existsSync(popupHtmlSrc)) {
        if (!existsSync(resolve(DIST, "popup"))) mkdirSync(resolve(DIST, "popup"), { recursive: true });
        copyFileSync(popupHtmlSrc, popupHtmlDst);
      }

      const stylesSrc = resolve(ROOT, "src", "content-script", "styles.css");
      const stylesDst = resolve(DIST, "styles.css");
      if (existsSync(stylesSrc)) copyFileSync(stylesSrc, stylesDst);
    },
  };
}

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
  plugins: [copyStaticAssets()],
});
