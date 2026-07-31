# Popup 改写方案：酒店初始化 + ReplySettings 配置

## 现状

当前 popup 只有：
- 状态显示
- API 地址输入
- 「生成回复」按钮
- 「取消」按钮

Content Script 浮层中已有的 ⚙ 设置（酒店选择 + ReplySettings 编辑）对用户来说入口太深。

## 目标

Popup 的三个状态对应三个视图：

```
状态 1：无酒店（首次使用）
┌──────────────────────┐
│  酒店评论AI助手        │
│                       │
│  欢迎使用              │
│  请先创建酒店配置        │
│                       │
│  酒店名称 [          ] │
│  所在城市 [          ] │
│                       │
│  [创建酒店]            │
│                       │
│  API: [http://...]    │
└──────────────────────┘

状态 2：有酒店
┌──────────────────────┐
│  酒店评论AI助手        │
│                       │
│  🏨 深圳湾XX酒店       │
│                       │
│  回复语气: 专业、温暖   │
│  回复风格: 正式...      │
│  规则: 投诉先道歉...     │
│                       │
│  [编辑设置]  [生成回复]  │
│                       │
│  API: [http://...]    │
└──────────────────────┘

状态 3：编辑设置（在 Popup 内完成，无需打开浮层）
┌──────────────────────┐
│  酒店评论AI助手        │
│                       │
│  回复设置              │
│                       │
│  回复语气 [          ] │
│  回复风格 [          ] │
│  规则 [              ] │
│     [每行一条]         │
│                       │
│  [返回]  [保存设置]     │
└──────────────────────┘
```

## 需要做的修改

### 1. 后端：新增 `POST /api/hotels` 创建酒店

Popup 创建酒店时，后端需要：
1. 生成 `hotel_id`（自增或 UUID）
2. 创建酒店目录 `resources/hotels/{hotel_id}/`
3. 生成默认的 `metadata.yaml`、`profile.yaml`、`policies.yaml`、`voice.yaml`
4. 返回 `{ hotel_id, hotel_name }`

**改动文件**：
| 文件 | 改动 |
|------|------|
| `api/hotel_config.py` | 新增 `POST /api/hotels` 端点 |
| `shared/hotel_config/repository.py` | 新增 `create_hotel(name, city)` 抽象方法 |
| `shared/hotel_config/yaml_repo.py` | 实现 `create_hotel()`：写 4 个 YAML 文件 + 生成默认 seed 数据 |
| `shared/hotel_config/service.py` | 新增 `create_hotel(name, city)` 方法 |

### 2. Popup 重写

Popup 从简单状态显示改为三视图路由，数据全部走后端 API。

**改动文件**：
| 文件 | 改动 |
|------|------|
| `popup/index.html` | 重构 HTML 结构为三视图容器 |
| `popup/popup.js` | 重写为三状态路由 + Hotel Config Service 的完整客户端 |
| `background/service-worker.js` | 不需要改（Popup 直连后端 API） |
| `content-script/index.js` | 不需要改（浮层 ⚙ 保持，只是 popup 也提供入口） |

### 3. Popup JS 逻辑

核心函数：

```javascript
// 状态路由
async function renderView() {
  const hotel = await getCurrentHotel();
  if (!hotel) return renderCreateHotelView();
  return renderHotelView(hotel);
}

// 创建酒店
async function createHotel(name, city) {
  const resp = await fetch(`${apiUrl}/api/hotels`, {
    method: 'POST',
    body: JSON.stringify({ name, city }),
  });
  const hotel = await resp.json();
  await setCurrentHotel({ hotel_id: hotel.hotel_id, hotel_name: hotel.name });
  return hotel;
}

// 加载配置
async function loadSettings(hotelId) {
  const resp = await fetch(`${apiUrl}/api/hotels/${hotelId}/reply-settings`);
  return await resp.json();
}

// 保存配置
async function saveSettings(hotelId, settings) {
  await fetch(`${apiUrl}/api/hotels/${hotelId}/reply-settings`, {
    method: 'PUT',
    body: JSON.stringify(settings),
  });
}
```

### 4. 不做的

- ❌ 不改 Content Script 浮层（现有 ⚙ 按钮的酒店选择 + 设置编辑保留，但 Popup 成为主入口）
- ❌ 不改 Service Worker
- ❌ 不修改 workflow 流程

## 数据流

```
Popup
  │
  ├─ 创建酒店 → POST /api/hotels { name, city }
  │               → YamlRepo.create_hotel() 生成 4 个 seed YAML
  │               → 返回 { hotel_id, hotel_name }
  │               → chrome.storage.local.set({ current_hotel })
  │
  ├─ 加载配置 → GET /api/hotels/{id}/reply-settings
  │               → 返回 { tone, style, rules }
  │               → 渲染到 Popup 预览
  │
  ├─ 编辑配置 → PUT /api/hotels/{id}/reply-settings { tone, style, rules }
  │               → YamlRepo.update_reply_settings() 写 voice.yaml
  │
  └─ 生成回复 → 同现有流程（走 Service Worker + POST /review/run）
```

## 测试

| 测试 | 覆盖 |
|------|------|
| `test_create_hotel` | YamlRepo.create_hotel() 生成目录 + 4 个 YAML 文件 |
| `test_create_hotel_duplicate` | 重复创建检查 |
| `test_list_hotels_after_create` | 创建后列表包含新酒店 |
| `test_api_create_hotel` | `POST /api/hotels` 端点 |
