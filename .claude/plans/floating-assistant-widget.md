# 演进：从 Popup 主 UI → Floating Assistant Widget

## 当前架构的问题

```
Popup（主入口）
  ├─ 创建酒店（用户首次打开时）
  ├─ 酒店首页（配置预览）
  ├─ 编辑设置
  └─ 生成回复 → 关闭 Popup → Content Script 显示浮层

Content Script（只有浮层，无 FAB）
  └─ 由 Service Worker 的 WORKFLOW_STARTED 触发显示
  └─ ⚙ 设置面板（有酒店选择逻辑，不应该在这里）
```

问题：
1. Popup 关闭后用户无法主动触发浮层
2. Content Script 的酒店选择逻辑不应存在（酒店由 Popup 管理）
3. 生成回复的操作链路过长：Popup→关闭→等待浮层

## 目标架构

```
Popup（配置控制台）
  ├─ 创建酒店
  ├─ 切换酒店
  ├─ 编辑 ReplySettings
  └─ 删除 API 地址 ×（已完成）

Content Script（Floating Assistant Widget）
  ├─ FAB 按钮（右下角悬浮）
  ├─ 主面板（生成回复、编辑、发布）
  ├─ 设置面板（只读展示当前酒店+设置，不可修改）
  └─ 酒店选择提示（如果无酒店）

Background（保持不变）
  ├─ 消息路由
  ├─ SSE 管理
  └─ API 通信
```

## 具体改动

### 1. Content Script

| 改动 | 说明 |
|------|------|
| 新增 FAB 按钮 | `init()` 时注入一个右下角悬浮圆形按钮，点击展开面板 |
| 精简面板 | 去掉 ⚙ 设置按钮（设置移到 Popup），去掉酒店选择 |
| 新增「编辑回复」| 生成的回复可编辑（textarea） |
| 新增「确认发布」| 将回复填入页面回复框 + 触发提交 |
| 新增「重新生成」| 失败时的补救 |
| 悬浮按钮常驻 | 始终显示在页面右下角 |

**删除的代码**：
- `getSettingsPanelHTML()` 和所有 settings 相关函数
- `getHotelSelectorHTML()` 和酒店选择逻辑
- `switchToSettings()`、`showSettingsForHotel()`、`renderSettings()`
- `_loadReplySettings()`、`_saveReplySettings()`、`_fetchHotelList()`

**保持的代码**：
- `getReviewContent()`（DOM 读取）
- `submitReply()`（DOM 写入）
- `handleMessage()` 和 WORKFLOW_* 处理（SSE 事件消费）
- `showFloatingPanel()` / `hideFloatingPanel()`
- CSS 样式（精简）

### 2. Popup

| 改动 | 说明 |
|------|------|
| 保持现有三视图 | 创建酒店、酒店首页、编辑设置 |
| 改为纯配置工具 | 没有生成回复按钮，酒店运营人员来这里配置 |
| 生成回复入口移到 Widget | |

### 3. 交互流程

```
用户在 OTA 页面浏览评论
        │
        │ 右下角始终有 AI 悬浮按钮
        ▼
点击 FAB → 浮层面板展开
        │
        ├─ 无酒店 → 「请先在 Popup 中选择酒店」
        ├─ 选中评论 → 显示评论内容 + [生成回复]
        ├─ 生成中 → 流式输出
        ├─ 生成完成 → 大按钮：[编辑回复] [确认发布] [重新生成]
        └─ 确认发布 → 填入 OTA 页面回复框 + 触发提交
```

### 4. 不做

- ❌ 不把设置 UI 放到 Widget（Popup 是配置入口）
- ❌ 不改动后端 API
- ❌ 不改 Service Worker
