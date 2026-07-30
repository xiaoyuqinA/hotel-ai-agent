/**
 * Content Script — Floating Assistant Widget
 *
 * 职责：
 * 1. FAB 按钮 + Floating Panel UI
 * 2. 通过 OTAAdapter 读取评论 / 填充回复 / 发布
 * 3. 消费 Service Worker 的 workflow 事件
 *
 * 配置管理（酒店、ReplySettings）由 Popup 负责。
 * Widget 只消费、不修改配置。
 */

import { createStore } from '../state/workflow-store.js';
import type { OTAAdapter } from './adapters/types.js';
import { detectAdapter } from './adapters/registry.js';
import { LocalHotelConfigRepository } from '../config/local_repository.js';
import { HotelConfigService } from '../config/service.js';

const store = createStore();
const configService = new HotelConfigService(new LocalHotelConfigRepository());

let _adapter: OTAAdapter | null = null;
let _currentReview = '';
async function getAdapter(): Promise<OTAAdapter | null> {
  if (!_adapter) _adapter = await detectAdapter();
  return _adapter;
}

// ── Hotel Context（只读，通过 ConfigService） ────────────────────────────────

/**
 * 获取当前酒店配置（只读）
 * 通过 ConfigService 而非直接操作 chrome.storage
 * 扩展上下文失效时自动等待重连
 */
async function _getCurrentHotel() {
  // 通过 PING 检查 runtime 是否真正可用
  const valid = await _isRuntimeValid();
  if (!valid) {
    console.warn('[AssistantWidget] Runtime invalid (PING failed), waiting for reconnect...');
    const ready = await _ensureRuntimeReady();
    if (!ready) {
      console.warn('[AssistantWidget] Runtime recovery failed, returning null');
      return null;
    }
    // 重新初始化 adapter
    getAdapter().then(a => a?.initialize?.());
  }

  try {
    return await configService.getCurrentHotel();
  } catch (e) {
    console.warn('[AssistantWidget] Failed to get current hotel:', e, (e as Error)?.message);
    return null;
  }
}

/**
 * 获取当前酒店完整的 HotelConfig（含 reply_settings）
 */
async function _getCurrentHotelConfig() {
  const current = await _getCurrentHotel();
  if (!current) return null;
  return configService.getHotel(current.hotel_id);
}

// ── 初始化 ─────────────────────────────────────────────────────────────────

/**
 * 检测扩展上下文是否有效（通过发送测试消息验证）
 */
async function _isRuntimeValid(): Promise<boolean> {
  try {
    if (!chrome.runtime?.id) return false;
    // 发送 PING 验证连接真正可用
    const resp = await chrome.runtime.sendMessage({ type: 'PING' }).catch(() => null);
    return resp?.pong === true;
  } catch {
    return false;
  }
}

/**
 * 等待 Service Worker 就绪（上下文失效时重试）
 */
async function _ensureRuntimeReady(maxRetries = 10, interval = 500): Promise<boolean> {
  for (let i = 0; i < maxRetries; i++) {
    if (await _isRuntimeValid()) return true;
    // 尝试重建连接（触发 Service Worker 重启）
    try {
      const resp = await chrome.runtime.sendMessage({ type: 'PING' }).catch(() => null);
      if (resp) return true;
    } catch { /* 忽略 */ }
    await new Promise(r => setTimeout(r, interval));
  }
  return false;
}

function init() {
  // 注册消息监听
  chrome.runtime.onMessage.addListener(handleMessage);
  injectStyles();
  injectFAB();
  getAdapter().then(a => a?.initialize?.());

  // 监听 Service Worker 重启（断开 → 重连）
  chrome.runtime.onConnect.addListener(() => {
    console.log('[AssistantWidget] runtime reconnected');
  });

  console.log('[AssistantWidget] initialized');
}

// ── 消息处理（来自 Service Worker） ──────────────────────────────────────────

function handleMessage(message, sender, sendResponse) {
  const { type, payload } = message;

  switch (type) {
    case 'WORKFLOW_STARTED':
      handleWorkflowStarted(payload);
      break;
    case 'STATUS_UPDATE':
      handleStatusUpdate(payload);
      break;
    case 'TOKEN_DELTA':
      handleTokenDelta(payload);
      break;
    case 'WORKFLOW_COMPLETED':
      handleWorkflowCompleted(payload);
      break;
    case 'WORKFLOW_ERROR':
      handleWorkflowError(payload);
      break;
    default:
      break;
  }

  sendResponse({ received: true });
  return true;
}

async function handleWorkflowStarted(payload) {
  await showPanel();
  setPanelView('running');
}

function handleStatusUpdate(payload) {
  updateStatus(payload.status, payload.message);
}

function handleTokenDelta(payload) {
  store.handleEvent({ kind: 'token_delta', delta: payload.delta, category: 'message' });
  updateReplyContent(store.getReply());
}

function handleWorkflowCompleted(payload) {
  store.handleEvent({ kind: 'workflow_completed', result: payload.result, category: 'system' });
  updateStatus('completed', payload.status || '回复生成完成');
  // replyContent 已由 token_delta 流式累积，不再覆盖
  setPanelView('completed');
}

function handleWorkflowError(payload) {
  store.setError(payload.error);
  updateStatus('error', payload.error);
  setPanelView('error');
}

// ── FAB 按钮 ────────────────────────────────────────────────────────────────

let fab = null;

function injectFAB() {
  if (document.getElementById('hotel-ai-fab')) return;

  fab = document.createElement('div');
  fab.id = 'hotel-ai-fab';
  fab.className = 'hotel-ai-fab';
  fab.innerHTML = '<span>✦</span>';
  fab.title = 'AI 回复助手';

  fab.addEventListener('click', (e) => {
    e.stopPropagation();
    togglePanel();
  });

  document.body.appendChild(fab);
}

function setFABState(state) {
  if (!fab) return;
  fab.dataset.state = state;
}

// ── Floating Panel ─────────────────────────────────────────────────────────

let panel = null;

function togglePanel() {
  if (panel && !panel.classList.contains('hidden')) {
    hidePanel();
  } else {
    showPanel();
  }
}

async function showPanel() {
  if (!panel) {
    panel = document.createElement('div');
    panel.id = 'hotel-ai-panel';
    panel.className = 'hotel-ai-panel hidden';
    document.body.appendChild(panel);
  }

  panel.classList.remove('hidden');

  await _getCurrentHotel(); // 确保 hotel 加载完成（酒店为可选）

  // 首次展示：初始化为 idle；非首次：保持当前视图（completed/failed 等）
  if (!panel.dataset.view) {
    store.reset();
    setPanelView('idle');
  }

  setFABState('active');
}

function hidePanel() {
  if (panel) panel.classList.add('hidden');
  setFABState('idle');
}

function dismissPanel() {
  hidePanel();
  store.reset();
  if (panel) delete panel.dataset.view;
}

// ── Panel Views ────────────────────────────────────────────────────────────

function setPanelView(view) {
  if (!panel) return;
  panel.dataset.view = view;

  switch (view) {
    case 'no-hotel':   renderNoHotel(); break;
    case 'idle':       renderIdle(); break;
    case 'running':    renderRunning(); break;
    case 'completed':  renderCompleted(); break;
    case 'error':      renderError(); break;
    case 'editing':    renderEditing(); break;
    case 'publishing': renderPublishing(); break;
    case 'published':  renderPublished(); break;
  }
}

function renderHeader() {
  return `
    <div class="ha-panel-header">
      <span class="ha-panel-title">✦ AI 回复助手</span>
      <div class="ha-panel-actions">
        <button class="ha-btn-icon" id="ha-minimize-btn" title="最小化">−</button>
        <button class="ha-btn-icon" id="ha-close-btn" title="关闭">×</button>
      </div>
    </div>
  `;
}

function renderNoHotel() {
  panel.innerHTML = renderHeader() + `
    <div class="ha-panel-body">
      <div class="ha-empty">
        <p>请先在扩展中创建或选择酒店</p>
        <p style="font-size:12px;color:#999;margin-top:8px;">
          点击 Chrome 工具栏的扩展图标打开配置
        </p>
      </div>
    </div>
  `;
  bindHeaderEvents();
}

async function renderIdle() {
  const hotel = await _getCurrentHotel();
  const adapter = await getAdapter();
  const ctx = adapter ? await adapter.getReview() : null;
  const review = ctx?.content || '';
  console.log('[AssistantWidget] renderIdle → review from adapter:', review, '(ctx:', ctx, ')');
  
  panel.innerHTML = renderHeader() + `
    <div class="ha-panel-body">
      <div class="ha-hotel-badge">
        ${hotel ? `🏨 ${hotel.hotel_name}` : `✨ 默认回复模式`}
      </div>
      ${!hotel ? `<div class="ha-tip">配置酒店后可自定义回复语气</div>` : ''}
      <div class="ha-review-box" id="ha-review-text">
        ${review || '<span class="ha-placeholder">选中评论后，点击「生成回复」</span>'}
      </div>
      <button class="ha-btn ha-btn-primary" id="ha-generate-btn">AI生成回复</button>
    </div>
  `;
  bindHeaderEvents();
  document.getElementById('ha-generate-btn').addEventListener('click', onGenerate);

  _setupSelectionWatcher();
}

let _selectionWatcher: (() => void) | null = null;

function _setupSelectionWatcher() {
  _selectionWatcher?.();
  const handler = () => {
    const sel = window.getSelection()?.toString().trim() ?? '';
    if (sel) {
      const reviewBox = document.getElementById('ha-review-text');
      if (reviewBox) {
        reviewBox.textContent = sel;
        reviewBox.classList.remove('ha-placeholder');
      }
    }
  };
  let timer: ReturnType<typeof setTimeout> | null = null;
  const debounced = () => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(handler, 150);
  };
  document.addEventListener('selectionchange', debounced);
  _selectionWatcher = () => {
    document.removeEventListener('selectionchange', debounced);
    if (timer) clearTimeout(timer);
  };
}

function renderRunning() {
  panel.innerHTML = renderHeader() + `
    <div class="ha-panel-body">
      <div class="ha-status-bar running">
        <span class="ha-status-dot"></span>
        <span class="ha-status-text" id="ha-status-text">正在生成回复...</span>
      </div>
      <div class="ha-reply-box streaming" id="ha-reply-box">
        <span class="ha-placeholder">等待回复...</span>
      </div>
    </div>
  `;
  bindHeaderEvents();
}

function renderCompleted() {
  const reply = store.getReply() || '';
  const review = _currentReview;

  panel.innerHTML = renderHeader() + `
    <div class="ha-panel-body">
      <div class="ha-status-bar completed">
        <span class="ha-status-dot"></span>
        <span class="ha-status-text">回复已生成</span>
      </div>
      ${review ? `<div class="ha-review-box"><strong>评论：</strong>${review}</div>` : ''}
      <div class="ha-reply-box" id="ha-reply-box">${reply || '（空回复）'}</div>
      <div class="ha-actions">
        <button class="ha-btn ha-btn-secondary" id="ha-edit-btn">✎ 编辑回复</button>
        <button class="ha-btn ha-btn-primary" id="ha-publish-btn">确认发布</button>
      </div>
      <button class="ha-btn ha-btn-text" id="ha-retry-btn">重新生成</button>
    </div>
  `;
  bindHeaderEvents();
  document.getElementById('ha-edit-btn').addEventListener('click', () => setPanelView('editing'));
  document.getElementById('ha-publish-btn').addEventListener('click', onPublish);
  document.getElementById('ha-retry-btn').addEventListener('click', onGenerate);
}

function renderPublishing() {
  panel.innerHTML = renderHeader() + `
    <div class="ha-panel-body">
      <div class="ha-status-bar running">
        <span class="ha-status-dot"></span>
        <span class="ha-status-text">正在发布到 OTA...</span>
      </div>
      <div style="text-align:center;padding:20px;color:#999;">
        <div style="font-size:28px;margin-bottom:10px;">⏳</div>
        <p>正在将回复填入页面并提交</p>
      </div>
    </div>
  `;
  bindHeaderEvents();
}

function renderPublished() {
  panel.innerHTML = renderHeader() + `
    <div class="ha-panel-body">
      <div class="ha-status-bar completed">
        <span class="ha-status-dot"></span>
        <span class="ha-status-text">已发布</span>
      </div>
      <div style="text-align:center;padding:20px;color:#52c41a;font-size:15px;">
        ✅ 回复已发布到 OTA 平台
      </div>
      <button class="ha-btn ha-btn-primary" id="ha-done-btn">完成</button>
    </div>
  `;
  bindHeaderEvents();
  document.getElementById('ha-done-btn').addEventListener('click', dismissPanel);
}

function renderError() {
  const error = store.getError() || '未知错误';

  panel.innerHTML = renderHeader() + `
    <div class="ha-panel-body">
      <div class="ha-status-bar error">
        <span class="ha-status-dot"></span>
        <span class="ha-status-text">操作失败</span>
      </div>
      <div class="ha-error-box">${error}</div>
      <button class="ha-btn ha-btn-primary" id="ha-retry-btn">重试</button>
    </div>
  `;
  bindHeaderEvents();
  document.getElementById('ha-retry-btn').addEventListener('click', onGenerate);
}

function renderEditing() {
  const reply = store.getReply() || '';

  panel.innerHTML = renderHeader() + `
    <div class="ha-panel-body">
      <div class="ha-status-bar">
        <span class="ha-status-dot"></span>
        <span class="ha-status-text">编辑回复</span>
      </div>
      <textarea class="ha-edit-textarea" id="ha-edit-textarea" rows="6">${reply}</textarea>
      <div class="ha-actions">
        <button class="ha-btn ha-btn-secondary" id="ha-edit-cancel-btn">取消</button>
        <button class="ha-btn ha-btn-primary" id="ha-edit-confirm-btn">确认</button>
        <button class="ha-btn ha-btn-primary" id="ha-edit-publish-btn">确认并发布</button>
      </div>
    </div>
  `;
  bindHeaderEvents();

  const textarea = document.getElementById('ha-edit-textarea');
  document.getElementById('ha-edit-cancel-btn').addEventListener('click', () => setPanelView('completed'));
  document.getElementById('ha-edit-confirm-btn').addEventListener('click', () => {
    store.setReply(textarea.value);
    setPanelView('completed');
  });
  document.getElementById('ha-edit-publish-btn').addEventListener('click', () => {
    store.setReply(textarea.value);
    onPublish();
  });
}

function bindHeaderEvents() {
  const minimizeBtn = document.getElementById('ha-minimize-btn');
  const closeBtn = document.getElementById('ha-close-btn');
  if (minimizeBtn) minimizeBtn.addEventListener('click', hidePanel);
  if (closeBtn) closeBtn.addEventListener('click', dismissPanel);
}

// ── 核心业务 ─────────────────────────────────────────────────────────────────

async function onGenerate() {
  const hotel = await _getCurrentHotel();
  const hotelId = hotel?.hotel_id ?? null;

  const adapter = await getAdapter();
  if (!adapter) {
    updateStatus('error', '当前页面不支持');
    setPanelView('idle');
    return;
  }

  const ctx = await adapter.getReview();
  const review = ctx?.content ?? '';
  if (!review) {
    updateStatus('error', '无法获取评论内容');
    setPanelView('idle');
    return;
  }

  _currentReview = review;
  store.startRun(null, hotelId);
  setPanelView('running');
  setFABState('generating');

  // 携带 hotel_context 发送（含 reply_settings，未来可用于后端）
  const hotelConfig = hotelId ? await _getCurrentHotelConfig() : null;
  const replySettings = hotelConfig?.reply_settings;

  // 扩展上下文可能已失效，兜底
  try {
    if (!chrome.runtime?.id) {
      updateStatus('error', '扩展已刷新，请重试');
      setPanelView('error');
      return;
    }

    chrome.runtime.sendMessage({
      type: 'GENERATE_REPLY',
      payload: {
        review,
        hotel_context: hotelConfig ? {
          hotel_id: hotelId,
          name: hotelConfig.name,
          reply_settings: replySettings,
        } : null,
      },
    });
  } catch (e) {
    console.error('[AssistantWidget] sendMessage failed:', e);
    store.setError('扩展连接异常，请刷新页面后重试');
    setPanelView('error');
  }
}

async function onPublish() {
  const reply = store.getReply();
  if (!reply) return;

  setPanelView('publishing');

  const adapter = await getAdapter();
  if (!adapter) {
    store.setError('无可用 Adapter');
    setPanelView('error');
    return;
  }

  const filled = await adapter.fillReply(reply);

  if (!filled) {
    store.setError('无法找到 OTA 页面回复框');
    setPanelView('error');
    return;
  }

  // MVP: publish() 会 throw，不自动发布，回复已填入让用户手动确认
  try {
    await adapter.publish();
    setPanelView('published');
    setTimeout(() => dismissPanel(), 2000);
    setFABState('idle');
  } catch {
    updateStatus('completed', '回复已填入，请手动发布');
    setPanelView('completed');
  }
}

// ── UI 更新 ─────────────────────────────────────────────────────────────────

function updateStatus(type, message) {
  const el = document.getElementById('ha-status-text');
  if (el) el.textContent = message || '';
}

function updateReplyContent(content) {
  const box = document.getElementById('ha-reply-box');
  if (!box) return;
  box.textContent = content || '';
}

// ── Styles ──────────────────────────────────────────────────────────────────

function injectStyles() {
  if (document.getElementById('hotel-ai-widget-styles')) return;

  const style = document.createElement('style');
  style.id = 'hotel-ai-widget-styles';
  style.textContent = getStyles();
  document.head.appendChild(style);
}

function getStyles() {
  return `
    #hotel-ai-fab {
      position: fixed; right: 24px; bottom: 24px;
      width: 52px; height: 52px; border-radius: 50%;
      background: linear-gradient(135deg,#667eea 0%,#764ba2 100%);
      color: white; font-size: 22px;
      display: flex; align-items: center; justify-content: center;
      cursor: pointer; z-index: 2147483647;
      box-shadow: 0 4px 16px rgba(102,126,234,0.4);
      transition: transform 0.2s, box-shadow 0.2s;
      user-select: none;
    }
    #hotel-ai-fab:hover { transform: scale(1.05); box-shadow: 0 6px 20px rgba(102,126,234,0.5); }
    #hotel-ai-fab[data-state="generating"] { animation: ha-pulse 1s infinite; }
    @keyframes ha-pulse { 0%,100%{box-shadow:0 4px 16px rgba(102,126,234,0.4)} 50%{box-shadow:0 4px 24px rgba(102,126,234,0.7)} }

    #hotel-ai-panel {
      position: fixed; right: 24px; bottom: 88px;
      width: 380px; max-width: calc(100vw - 48px);
      max-height: calc(100vh - 120px);
      background: white; border-radius: 12px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.18);
      z-index: 2147483646;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px; overflow: hidden;
      display: flex; flex-direction: column;
    }
    #hotel-ai-panel.hidden { display: none; }

    .ha-panel-header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 12px 16px;
      background: linear-gradient(135deg,#667eea 0%,#764ba2 100%);
      color: white; flex-shrink: 0;
    }
    .ha-panel-title { font-weight: 600; font-size: 15px; }
    .ha-panel-actions { display: flex; gap: 6px; }
    .ha-btn-icon {
      background: rgba(255,255,255,0.2); border: none; color: white;
      width: 28px; height: 28px; border-radius: 6px; cursor: pointer;
      font-size: 16px; display: flex; align-items: center; justify-content: center;
    }
    .ha-btn-icon:hover { background: rgba(255,255,255,0.3); }
    .ha-panel-body { padding: 14px 16px 16px; overflow-y: auto; flex: 1; min-height: 180px; }
    .ha-hotel-badge { font-size: 13px; font-weight: 500; color: #555; margin-bottom: 10px; }

    .ha-review-box {
      min-height: 60px; max-height: 100px; overflow-y: auto;
      padding: 10px 12px; background: #f9f9f9;
      border: 1px solid #eee; border-radius: 8px;
      font-size: 13px; line-height: 1.5; color: #333; margin-bottom: 10px;
    }
    .ha-review-box .ha-placeholder { color: #bbb; font-style: italic; }

    .ha-reply-box {
      min-height: 100px; max-height: 200px; overflow-y: auto;
      padding: 12px; background: #fafafa;
      border: 1px solid #eee; border-radius: 8px;
      font-size: 14px; line-height: 1.6; color: #333;
      margin-bottom: 10px; white-space: pre-wrap;
    }
    .ha-reply-box.streaming { border-color: #667eea; }

    .ha-actions { display: flex; gap: 8px; margin-bottom: 8px; }
    .ha-btn {
      flex: 1; padding: 10px; border: none; border-radius: 8px;
      font-size: 14px; font-weight: 500; cursor: pointer; transition: all 0.2s;
    }
    .ha-btn-primary { background: linear-gradient(135deg,#667eea 0%,#764ba2 100%); color: white; }
    .ha-btn-primary:hover { opacity: 0.9; }
    .ha-btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .ha-btn-secondary { background: #f0f0f0; color: #555; }
    .ha-btn-secondary:hover { background: #e5e5e5; }
    .ha-btn-text {
      background: none; border: 1px solid #ddd; color: #999; font-size: 13px; padding: 8px;
    }
    .ha-btn-text:hover { border-color: #667eea; color: #667eea; }

    .ha-status-bar {
      display: flex; align-items: center; gap: 8px;
      padding: 8px 10px; background: #f5f5f5;
      border-radius: 8px; margin-bottom: 10px; font-size: 13px; color: #666;
    }
    .ha-status-dot { width: 8px; height: 8px; border-radius: 50%; background: #ccc; flex-shrink: 0; }
    .ha-status-bar.running .ha-status-dot { background: #52c41a; animation: ha-pulse-dot 1s infinite; }
    .ha-status-bar.completed .ha-status-dot { background: #52c41a; }
    .ha-status-bar.error .ha-status-dot { background: #ff4d4f; }
    @keyframes ha-pulse-dot { 0%,100%{opacity:1} 50%{opacity:0.5} }

    .ha-error-box {
      padding: 10px 12px; background: #fff2f0; border: 1px solid #ffccc7;
      border-radius: 8px; color: #ff4d4f; font-size: 13px; margin-bottom: 10px;
    }

    .ha-edit-textarea {
      width: 100%; padding: 10px 12px; border: 1px solid #ddd;
      border-radius: 8px; font-size: 14px; font-family: inherit;
      resize: vertical; min-height: 120px; outline: none; margin-bottom: 10px;
    }
    .ha-edit-textarea:focus { border-color: #667eea; }

    .ha-empty { text-align: center; padding: 30px 0; color: #999; font-size: 14px; }
    .ha-tip { font-size: 12px; color: #999; margin-bottom: 10px; padding: 6px 8px; background: #f9f9f9; border-radius: 6px; }
  `;
}

// ── 初始化 ───────────────────────────────────────────────────────────────────

init();
