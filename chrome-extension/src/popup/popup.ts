/**
 * Popup Script — 三视图路由
 *
 * 视图 1：创建酒店（首次使用）
 * 视图 2：酒店首页（现有酒店，展示配置概览）
 * 视图 3：编辑设置（ReplySettings 编辑）
 */

const CURRENT_HOTEL_KEY = 'current_hotel';

// DOM
let contentEl;

// ── 工具函数 ─────────────────────────────────────────────────────────────────

async function getApiUrl() {
  const resp = await chrome.runtime.sendMessage({ type: 'GET_API_URL' });
  return resp.apiUrl || 'http://localhost:8000';
}

async function getCurrentHotel() {
  const result = await chrome.storage.local.get(CURRENT_HOTEL_KEY);
  return result[CURRENT_HOTEL_KEY] || null;
}

async function setCurrentHotel(hotel) {
  await chrome.storage.local.set({ [CURRENT_HOTEL_KEY]: hotel });
}

async function clearCurrentHotel() {
  await chrome.storage.local.remove(CURRENT_HOTEL_KEY);
}

function apiUrl(path) {
  return getApiUrl().then(base => `${base}${path}`);
}

// ── API ──────────────────────────────────────────────────────────────────────

async function apiFetch(method, path, body = null) {
  const url = await apiUrl(path);
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);

  const resp = await fetch(url, opts);
  if (!resp.ok) {
    let detail = resp.statusText;
    try { const d = await resp.json(); detail = d.detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  if (resp.status === 204) return null;
  return await resp.json();
}

async function createHotel(name, city) {
  return await apiFetch('POST', '/api/hotels', { name, city });
}

async function listHotels() {
  return await apiFetch('GET', '/api/hotels');
}

async function loadSettings(hotelId) {
  return await apiFetch('GET', `/api/hotels/${hotelId}/reply-settings`);
}

async function saveSettings(hotelId, settings) {
  return await apiFetch('PUT', `/api/hotels/${hotelId}/reply-settings`, settings);
}

// ── 路由 ─────────────────────────────────────────────────────────────────────

async function render() {
  contentEl = document.getElementById('app-content');

  const hotel = await getCurrentHotel();
  if (!hotel) {
    return renderCreateHotel();
  }

  return renderHotelHome(hotel);
}

// ── 视图 1：创建酒店 ─────────────────────────────────────────────────────────

function renderCreateHotel(errorMsg) {
  contentEl.innerHTML = `
    <div class="section">
      <div class="label">欢迎使用</div>
      <p style="font-size:13px;color:#666;margin-bottom:12px;">
        请先创建酒店配置，开始使用 AI 回复助手
      </p>
      <input class="input" id="hotel-name-input"
             placeholder="酒店名称（如：深圳湾万豪酒店）"
             style="margin-bottom:8px;" />
      <input class="input" id="hotel-city-input"
             placeholder="所在城市（如：深圳）"
             style="margin-bottom:12px;" />
      <button class="btn btn-primary" id="create-hotel-btn">创建酒店</button>
      <div id="create-status" class="status-text ${errorMsg ? 'error' : ''}">
        ${errorMsg || ''}
      </div>
    </div>
  `;

  document.getElementById('create-hotel-btn').addEventListener('click', onCreateHotel);
}

async function onCreateHotel() {
  const name = document.getElementById('hotel-name-input').value.trim();
  const city = document.getElementById('hotel-city-input').value.trim();

  if (!name) {
    document.getElementById('create-status').textContent = '请输入酒店名称';
    document.getElementById('create-status').className = 'status-text error';
    return;
  }
  if (!city) {
    document.getElementById('create-status').textContent = '请输入所在城市';
    document.getElementById('create-status').className = 'status-text error';
    return;
  }

  const btn = document.getElementById('create-hotel-btn');
  btn.disabled = true;
  btn.textContent = '创建中...';

  try {
    const hotel = await createHotel(name, city);
    await setCurrentHotel({ hotel_id: hotel.hotel_id, hotel_name: hotel.hotel_name });
    await render();
  } catch (e) {
    document.getElementById('create-status').textContent = '创建失败：' + e.message;
    document.getElementById('create-status').className = 'status-text error';
    btn.disabled = false;
    btn.textContent = '创建酒店';
  }
}

// ── 视图 2：酒店首页 ─────────────────────────────────────────────────────────

async function renderHotelHome(hotel) {
  contentEl.innerHTML = `
    <div class="section">
      <div class="hotel-selector" id="hotel-selector-btn">
        <span class="icon">🏨</span>
        <span class="name">${hotel.hotel_name}</span>
        <span class="arrow">▼</span>
      </div>
    </div>

    <div class="section" id="settings-preview">
      <div class="label">回复配置</div>
      <div style="text-align:center;padding:20px;color:#999;font-size:13px;">
        加载中...
      </div>
    </div>

    <div class="section">
      <button class="settings-btn" id="edit-settings-btn">
        ✎ 编辑回复设置
      </button>
    </div>
  `;

  loadSettingsPreview(hotel.hotel_id);

  document.getElementById('hotel-selector-btn').addEventListener('click', onShowHotelList);
  document.getElementById('edit-settings-btn').addEventListener('click', () => renderEditSettings(hotel));
}

async function loadSettingsPreview(hotelId) {
  const container = document.getElementById('settings-preview');
  try {
    const settings = await loadSettings(hotelId);
    container.innerHTML = `
      <div class="label">回复配置</div>
      <div class="config-item">
        <div class="config-label">回复语气</div>
        <div class="config-value">${settings.tone || '未设置'}</div>
      </div>
      <div class="config-item">
        <div class="config-label">回复风格</div>
        <div class="config-value">${settings.style || '未设置'}</div>
      </div>
      <div class="config-item">
        <div class="config-label">回复规则</div>
        <div class="config-value">
          ${(settings.rules || []).map(r => '• ' + r).join('<br>') || '无'}
        </div>
      </div>
    `;
  } catch (e) {
    container.innerHTML = `
      <div class="label">回复配置</div>
      <div class="status-text error">加载失败：${e.message}</div>
    `;
  }
}

// ── 视图 3：编辑设置 ─────────────────────────────────────────────────────────

function renderEditSettings(hotel) {
  contentEl.innerHTML = `
    <div class="section">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
        <button class="btn btn-secondary" id="back-btn"
                style="width:auto;padding:6px 14px;font-size:13px;">← 返回</button>
        <span style="font-weight:500;">${hotel.hotel_name}</span>
      </div>
    </div>

    <div class="section">
      <div class="label">回复语气</div>
      <input class="input" id="edit-tone" placeholder="例如：专业、温暖、真诚"
             style="margin-bottom:10px;" />
      <div class="label">回复风格</div>
      <input class="input" id="edit-style" placeholder="例如：正式但具有人情味"
             style="margin-bottom:10px;" />
      <div class="label">回复规则（每行一条）</div>
      <textarea class="textarea" id="edit-rules" rows="4"
                placeholder="投诉必须先表达歉意"></textarea>

      <div class="btn-row">
        <button class="btn btn-secondary" id="cancel-edit-btn">取消</button>
        <button class="btn btn-primary" id="save-settings-btn">保存设置</button>
      </div>
      <div id="edit-status" class="status-text hidden"></div>
    </div>
  `;

  loadSettings(hotel.hotel_id).then(settings => {
    document.getElementById('edit-tone').value = settings.tone || '';
    document.getElementById('edit-style').value = settings.style || '';
    document.getElementById('edit-rules').value = (settings.rules || []).join('\n');
  }).catch(e => {
    document.getElementById('edit-status').textContent = '加载失败：' + e.message;
    document.getElementById('edit-status').className = 'status-text error';
  });

  document.getElementById('back-btn').addEventListener('click', () => render());
  document.getElementById('cancel-edit-btn').addEventListener('click', () => render());
  document.getElementById('save-settings-btn').addEventListener('click', () => onSaveSettings(hotel));
}

async function onSaveSettings(hotel) {
  const tone = document.getElementById('edit-tone').value.trim();
  const style = document.getElementById('edit-style').value.trim();
  const rulesRaw = document.getElementById('edit-rules').value.trim();
  const rules = rulesRaw ? rulesRaw.split('\n').map(r => r.trim()).filter(Boolean) : [];

  if (!tone) {
    document.getElementById('edit-status').textContent = '回复语气不能为空';
    document.getElementById('edit-status').className = 'status-text error';
    return;
  }

  const btn = document.getElementById('save-settings-btn');
  btn.disabled = true;
  btn.textContent = '保存中...';

  try {
    await saveSettings(hotel.hotel_id, { tone, style, rules });
    document.getElementById('edit-status').textContent = '✅ 设置已保存';
    document.getElementById('edit-status').className = 'status-text success';
    setTimeout(() => render(), 1200);
  } catch (e) {
    document.getElementById('edit-status').textContent = '保存失败：' + e.message;
    document.getElementById('edit-status').className = 'status-text error';
    btn.disabled = false;
    btn.textContent = '保存设置';
  }
}

// ── 酒店列表弹窗 ─────────────────────────────────────────────────────────────

async function onShowHotelList() {
  const modal = document.getElementById('hotel-list-modal');
  const hotels = await listHotels();
  const current = await getCurrentHotel();

  modal.innerHTML = `
    <div class="modal-content">
      <h3>选择酒店</h3>
      ${hotels.map(h => `
        <div class="modal-hotel-item" data-id="${h.hotel_id}" data-name="${h.hotel_name}">
          <div class="m-name">${h.hotel_name} ${current && current.hotel_id === h.hotel_id ? '✓' : ''}</div>
          <div class="m-id">${h.hotel_id}</div>
        </div>
      `).join('')}
      <div class="modal-new-hotel" id="modal-new-hotel-btn">+ 创建新酒店</div>
    </div>
  `;

  modal.querySelectorAll('.modal-hotel-item').forEach(el => {
    el.addEventListener('click', async () => {
      await setCurrentHotel({
        hotel_id: el.dataset.id,
        hotel_name: el.dataset.name,
      });
      modal.classList.add('hidden');
      await render();
    });
  });

  document.getElementById('modal-new-hotel-btn').addEventListener('click', async () => {
    await clearCurrentHotel();
    modal.classList.add('hidden');
    renderCreateHotel();
  });

  modal.classList.remove('hidden');
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.add('hidden');
  });
}

// ── 生成回复（通过 background） ──────────────────────────────────────────────



document.addEventListener('DOMContentLoaded', render);
