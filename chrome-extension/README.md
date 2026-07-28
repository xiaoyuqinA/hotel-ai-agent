# 酒店评论 AI 助手 - Chrome Extension

智能生成酒店评论回复的 Chrome 扩展。

## 架构

```
Chrome Extension
├── Content Script    → OTA 页面 DOM 读取 + 浮层 UI
├── Background Worker → API 通信 + SSE 长连接
└── Popup            → 配置 + 快捷操作
        │
        ▼
FastAPI Backend
        │
        ▼
LangGraph Runtime
```

## 文件结构

```
chrome-extension/
├── manifest.json              # 插件配置
├── api/
│   └── workflow-client.js    # API 客户端（POST + SSE）
├── background/
│   └── service-worker.js     # 后台进程（核心逻辑）
├── content-script/
│   ├── index.js               # DOM 读取 + UI 渲染
│   └── styles.css            # 备用样式
├── popup/
│   ├── index.html            # 弹出窗口
│   └── popup.js              # 快捷操作
├── state/
│   └── workflow-store.js     # 状态管理
└── icons/
    └── README.md              # 图标说明
```

## 安装

1. 打开 Chrome，访问 `chrome://extensions/`
2. 开启右上角「开发者模式」
3. 点击「加载已解压的扩展程序」
4. 选择 `chrome-extension` 文件夹

## 配置

1. 点击插件图标打开 Popup
2. 在「API 地址」输入框中配置后端地址（默认 `http://localhost:8000`）
3. 确保后端服务已启动

## 使用

### 方式 1：Popup

1. 在 OTA 页面选中评论文本
2. 点击插件图标
3. 点击「生成回复」
4. 回复生成后，点击「发送」提交到页面

### 方式 2：浮层

1. 打开 OTA 评论页面
2. 点击页面右下角的「生成回复」按钮
3. 等待回复生成（流式输出）
4. 点击「发送」提交

## 支持的 OTA 平台

- 携程 (ctrip.com)
- 飞猪 (fliggy.com)
- Booking (booking.com)
- Agoda (agoda.com)
- 途家 (tujia.com)

## 开发

```bash
# 1. 启动后端
cd /path/to/hotel-ai-agents
uvicorn api.main:app --reload

# 2. 加载插件到 Chrome
# - 打开 chrome://extensions/
# - 点击「重新加载」更新插件

# 3. 调试
# - 右键插件图标 → 检查弹出内容
# - 打开 Chrome DevTools → Service Worker
```

## 后端 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/review/run` | POST | 创建 workflow run |
| `/review/stream/{run_id}` | GET | SSE 订阅事件 |
| `/review/run/{run_id}` | GET | 查询 run 状态 |

## WorkflowEvent 事件类型

| category | kind | 说明 |
|----------|------|------|
| system | workflow_started | 工作流开始 |
| system | workflow_completed | 工作流完成 |
| system | workflow_failed | 工作流失败 |
| progress | node_started | 节点开始 |
| progress | node_completed | 节点完成 |
| message | token_delta | Token 流式输出 |
| state | state_updated | 状态更新 |
| tool | tool_call | 工具调用 |
