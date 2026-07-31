# Content Script 修复计划（P0 + P1）

## 目标

修复代码中的单酒店残留、增加 publishing 状态、抽象 OTA Adapter。

## 改动清单

### 1. P0：删除 hotel_001 fallback + 删除 ReplySettings 函数

```javascript
// onGenerate() — 删掉 fallback
- const hotelId = hotel ? hotel.hotel_id : 'hotel_001';
+ if (!hotel) { setPanelView('no-hotel'); return; }
+ const hotelId = hotel.hotel_id;

// 删除未使用的函数
- _loadReplySettings()
```

### 2. P0：增加 publishing 状态

Panel 新增 `publishing` 视图：

```
status: publishing

面板显示：
  "正在发布到 OTA..."
  无按钮

发布成功后 → dismissPanel()
发布失败   → 回到 completed + 显示错误
```

调用栈：

```
onPublish()
  → setPanelView('publishing')
  → 尝试 otaAdapter.fillReply(reply)
  → 尝试 otaAdapter.publish()
  → 成功 → dismissPanel()
  → 失败 → setPanelView('completed') + showError
```

store 不需要改（不涉及 workflow 状态）。

### 3. P0：抽象 OTA Adapter

新建 `chrome-extension/content-script/ota-adapter.js`。

接口设计：

```javascript
class OTAAdapter {
  /**
   * 获取当前页面的评论内容。
   * 优先级：用户选中 > OTA 特定选择器 > 通用 fallback
   */
  getReviewContent() {}

  /**
   * 将 AI 回复填入 OTA 页面的回复框。
   * 返回 true/false 表示成功/失败。
   */
  fillReply(text) {}

  /**
   * 尝试触发发布操作。
   * 返回 true/false。
   */
  publish() {}
}
```

index.js 中保留 `getReviewContent()` 和 `submitReplyToDOM()` 作为通用 fallback，但优先调用 OTAAdapter 子类。

当前阶段不用真正实现多 OTA 区分，只提取接口。以后加 CtripAdapter、MeituanAdapter 时只加新文件。

### 4. P1：Review 保存进 store

workflow-store.js 增加 `setReview()` / `getReview()`。

store 结构：

```javascript
state: {
  runId,
  status,
  replyContent,
  reviewContent,  // 新增
  hotelId,        // 新增
  error,
  lastSequence,
  events,
}
```

`onGenerate()` 调用时：

```javascript
store.setReview({ content: review, hotelId });
```

### 5. 不改的

- ❌ `current_hotel` 改 `current_context`（P1，后续独立修改）
- ❌ 不改 Service Worker（本次只修 Content Script）

## 文件改动

| 文件 | 改动 |
|------|------|
| `content-script/ota-adapter.js` | **新增**：OTAAdapter 基类 |
| `content-script/index.js` | 删 fallback、删 _loadReplySettings、增加 publishing 视图、使用 OTAAdapter |
| `state/workflow-store.js` | 新增 setReview/getReview |
