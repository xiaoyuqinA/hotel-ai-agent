# Workflow Session Runtime - Chrome Extension 实现计划

## 当前状态

代码骨架已基本实现，需要修复几个 bug 并优化协作流程。

---

## 待修复项

### 1. service-worker.js - 小写 bug
**文件**: `chrome-extension/background/service-worker.js:285`
**问题**: `session.run_id` 应为 `session.runId`
**影响**: Cancel 时调用后端 cancel API 会失败

### 2. SSEManager - sequence 更新时机
**文件**: `chrome-extension/background/sse-manager.js:126-134`
**问题**: 当前在 `onmessage` 中先更新 sequence，再调用 `onEvent`。但需要在 EventRouter 路由前确保 sequence 已更新
**优化**: 在事件路由前更新 session sequence（已正确实现，但需要确认）

### 3. 后端 Cancel API
**文件**: 后端 `api/main.py` 或 `api/sse.py`
**问题**: 代码中调用 `/review/run/{run_id}/cancel`，但后端可能没有实现
**需要**: 添加 cancel API 端点

---

## 实现计划

### Phase 1: 修复 Chrome Extension Bug
1. 修复 `service-worker.js` 中的 `run_id` → `runId`
2. 验证 sequence 更新流程
3. 测试 Service Worker 启动恢复流程

### Phase 2: 添加后端 Cancel API
1. 在 `api/sse.py` 添加 `POST /review/run/{run_id}/cancel` 端点
2. 更新 workflow_runs 表添加 cancel 标志
3. 在 WorkflowRuntime 中检测取消信号

### Phase 3: 集成测试
1. 端到端测试 workflow 生命周期
2. 测试断线重连
3. 测试 cancel 功能

---

## 文件清单

```
chrome-extension/
├── background/
│   ├── service-worker.js    # [修改] 修复 run_id bug
│   ├── session-manager.js   # [已实现] 无需修改
│   ├── sse-manager.js       # [已实现] 验证 sequence 流程
│   └── event-router.js      # [已实现] 无需修改
└── manifest.json            # [已存在] 无需修改

backend/
├── api/
│   ├── sse.py               # [新增] cancel endpoint
│   └── main.py              # [如需要]
└── shared/
    └── runtime/
        └── workflow_runtime.py  # [新增] cancel 信号检测
```

---

## 关键修改点

### 1. service-worker.js:285
```javascript
// 错误
await fetch(`${apiUrl}/review/run/${session.run_id}/cancel`)

// 正确
await fetch(`${apiUrl}/review/run/${session.runId}/cancel`)
```

### 2. api/sse.py - 添加 cancel endpoint
```python
@router.post("/review/run/{run_id}/cancel")
async def cancel_workflow(run_id: str):
    # 1. 标记 workflow_runs.canceled = True
    # 2. 返回 success
    pass
```

---

## 测试场景

1. **正常流程**: 创建 run → 接收事件 → 完成
2. **断线重连**: 创建 run → 断线 → 重连 → 继续接收
3. **Cancel**: 创建 run → 用户取消 → 后端停止 → UI 更新

---

## 时间估算

- Phase 1 (Bug Fix): 10 分钟
- Phase 2 (Backend Cancel): 30 分钟
- Phase 3 (Integration Test): 20 分钟
- **总计**: 约 1 小时
