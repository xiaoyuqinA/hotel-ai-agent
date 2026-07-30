import { defineConfig, loadEnv } from "vite";
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

/**
 * Chrome 内容脚本不支持 ES module import。
 * Vite 多入口构建会为 contentScript 生成共享 chunk 并产生 import 语句。
 *
 * 解决方案：两阶段构建
 *   1. 先构建 background + popup（共享 chunk 只影响它们，它们是 module 类型，没问题）
 *   2. 再单独构建 contentScript（单入口，不会产生共享 chunk，输出自包含）
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ROOT, 'VITE_');
  const apiUrl = JSON.stringify(env.VITE_API_URL || 'http://localhost:8000');
  return {
    define: {
      'import.meta.env.VITE_API_URL': apiUrl,
    },
    build: {
      outDir: DIST,
      emptyOutDir: true,
      rollupOptions: {
        input: {
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
    plugins: [
      copyStaticAssets(),
      // 第二阶段：单独构建 contentScript
      {
        name: "build-content-script",
        async closeBundle() {
          const { build } = await import("vite");
          await build({
            configFile: false,
            root: ROOT,
            define: {
              'import.meta.env.VITE_API_URL': apiUrl,
            },
            build: {
              outDir: DIST,
              emptyOutDir: false,
              rollupOptions: {
                input: resolve(ROOT, "src/content-script/index.ts"),
                output: {
                  entryFileNames: "contentScript.js",
                  format: "iife",
                },
              },
            },
          });
        },
      },
    ],
  };
});
