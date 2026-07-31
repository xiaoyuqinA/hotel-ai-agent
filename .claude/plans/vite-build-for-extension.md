# Vite 打包 Chrome Extension

## 问题

Chrome MV3 Content Script 不支持 `import`（即使 `"type": "module"` 也不可靠）。
Service Worker 虽然支持 module，但为了统一都用 Vite 打包。

## 方案

不改目录结构、不移动文件。只在 `chrome-extension/` 下加构建层。

### 目录变化

```
chrome-extension/
├── package.json          ← 新增
├── vite.config.js        ← 新增
├── dist/                 ← 构建产物
│   ├── manifest.json     ← copy
│   ├── contentScript.js  ← bundle
│   ├── background.js     ← bundle
│   ├── popup/
│   │   ├── index.html    ← copy
│   │   └── popup.js      ← bundle
│   ├── assets/           ← CSS 等
│   └── icons/            ← copy
│
├── manifest.json         ← 不变（引用构建产物路径）
├── content-script/       ← 不变
├── background/           ← 不变
├── popup/                ← 不变
├── state/                ← 不变
├── api/                  ← 不变
└── icons/                ← 不变
```

### vite.config.js

三个入口：
- `contentScript`：`content-script/index.js`
- `background`：`background/service-worker.js`
- `popup`：`popup/popup.html`

输出到 `dist/`。
HTML 文件由 vite 的 HTML 插件处理（自动注入打包后的 JS）。

### manifest.json 修改

指向构建产物：
```json
{
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [{
    "js": ["contentScript.js"]
  }],
  "action": {
    "default_popup": "popup/index.html"
  }
}
```

manifest.json 本身保留在 dist/ 中（由构建复制）。

### 构建命令

```bash
cd chrome-extension
npm install -D vite
npm run build
# → dist/ 目录生成
```

### 加载方式

Chrome 加载 `chrome-extension/dist/` 目录。

### 开发迭代

改源码后：
```bash
npm run build
# 再到 chrome://extensions 点击刷新
```

后续可以加 `--watch` 模式自动重建。

## 不变

- ❌ 不改目录结构（不移动文件到 src/）
- ❌ 不改 import 语句
- ❌ 不加 TypeScript（保持纯 JS）
- ❌ 不改 `workflow-store.js`、`ota-adapter.js`、`session-manager.js` 等被 import 的文件

只加构建层。
