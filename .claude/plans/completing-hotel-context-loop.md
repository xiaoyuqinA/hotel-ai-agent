# 补齐 Hotel Identity Context 闭环

## 当前缺口

```
Chrome Extension (content-script)
     │
     │ hotel_id = "hotel_001"  ← 硬编码
     │
     ▼
POST /review/run { reviews_content }
     │
     │ 没有 hotel_id 参数
     ▼
input_mapper: hotel_id = "hotel_001"  ← 默认
```

酒店身份在入口处丢失——用户可能在 hotel_002 的页面上操作，但回复用的是 hotel_001 的配置。

## 需要改的部分（共 4 处）

### 1. API: `GET /api/hotels` 返回酒店列表（含名称）

当前：`["hotel_001"]`
改后：`[{"hotel_id":"hotel_001","hotel_name":"深圳湾XX酒店"}]`

repository.list_hotel_ids() 同时读取 metadata.yaml 获取名称。

### 2. API: `POST /review/run` 接受 hotel_id 参数

当前：body = `{ reviews_content, thread_id }`
改后：body = `{ reviews_content, thread_id, hotel_id }`

hotel_id 通过 input_mapper 传入 workflow state。

### 3. Chrome Extension: 增加 CurrentHotel 上下文存储

删除 hardcode `hotel_001`，改为：

- `chrome.storage.local` 存储 `{ current_hotel: { hotel_id, hotel_name } }`
- 首次打开设置时如果无 current_hotel，显示酒店选择界面
- 生成回复时带上 hotel_id
- 设置页面从 current_hotel 获取 hotel_id 后再调用 API

### 4. Service Worker: 生成回复时传递 hotel_id

当前 `handleGenerateReply` 发送 `{ review }`，改为 `{ review, hotel_id }`。

## 数据流（改后完整链路）

```
                   Chrome Extension
                        │
                        │ chrome.storage.local → current_hotel
                        │
          ┌─────────────┴─────────────┐
          │                           │
  点击「生成回复」              点击 ⚙ 设置
          │                           │
          ▼                           ▼
 POST /review/run              GET /api/hotels/{hotel_id}
 {reviews_content,              /reply-settings
  hotel_id}
          │                           │
          ▼                           ▼
  input_mapper                  HotelConfigService
  → state.hotel_id = x          → YAML 读写
          │
          ▼
  load_hotel_context_node
  → HotelContextLoader.load(hotel_id)
  → HotelConfigService.get_reply_settings(hotel_id)
  → generate_reply_node
```

## 改动范围

| 层 | 文件 | 改动点 | 影响 |
|----|------|--------|------|
| API | `api/hotel_config.py` | `GET /api/hotels` 返回 `[{hotel_id, hotel_name}]` | 新增字段，向后兼容 |
| API | `api/sse.py` | `POST /review/run` 接受 hotel_id 参数 | 新增可选字段 |
| 后端 | `shared/hotel_config/repository.py` | 新增 `list_hotels()` 返回完整信息 | 接口扩展 |
| 后端 | `shared/hotel_config/yaml_repo.py` | `list_hotel_ids()` → `list_hotels()` 读取 metadata | 实现变更 |
| Extension | `content-script/index.js` | 新增 `getCurrentHotel()`、`setCurrentHotel()`、酒店选择 UI | 核心变更 |
| Extension | `content-script/index.js` | 生成回复时传递 hotel_id | 流程变更 |
| Extension | `background/service-worker.js` | `handleGenerateReply` 传递 hotel_id | 参数传递 |
| 测试 | `tests/unit/test_hotel_config.py` | 新增 list_hotels 测试 | 测试补全 |

## 不做

- ❌ 不新增任何数据表（YAML 足够）
- ❌ 不改 `HotelContext` 或 `ReplySettings` 模型
- ❌ 不做多酒店自动识别（URL 匹配等）— 交给用户手动选择
