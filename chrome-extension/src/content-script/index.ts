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
import { initI18n, setCurrentLang, normalizeLang, t } from '../i18n/index.js';

const store = createStore();
const configService = new HotelConfigService(new LocalHotelConfigRepository());

let _adapter: OTAAdapter | null = null;
let _currentReview = '';
async function getAdapter(): Promise<OTAAdapter | null> {
  if (!_adapter) _adapter = await detectAdapter();
  return _adapter;
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
  // 初始化语言（storage → 浏览器检测）
  initI18n().then((lang) => {
    setCurrentLang(lang);
    // 若面板已渲染，刷新文案
    if (panel) renderCurrentView();
  });

  // 语言切换（popup 修改 storage 时同步）
  try {
    chrome.storage.onChanged.addListener((changes, area) => {
      if (area === 'local' && changes['app_lang']) {
        setCurrentLang(normalizeLang(changes['app_lang'].newValue));
        if (panel) renderCurrentView();
      }
    });
  } catch { /* storage listener 不可用时忽略 */ }

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

  try { sendResponse({ received: true }); } catch { /* context invalidated */ }
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
  updateStatus('completed', payload.status || t('widget.reply_generated'));
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
  fab.title = t('widget.title');

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

  // hotel 配置由 Service Worker 在生成回复时自行读取
  // Content Script 不再需要主动获取 hotel 信息

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
  }
}

/** 按当前视图重新渲染（语言切换后刷新文案） */
function renderCurrentView() {
  if (!panel) return;
  setPanelView(panel.dataset.view || 'idle');
}

function renderHeader() {
  return `
    <div class="ha-panel-header">
      <span class="ha-panel-title">✦ ${t('widget.title')}</span>
      <div class="ha-panel-actions">
        <button class="ha-btn-icon" id="ha-minimize-btn" title="${t('widget.minimize')}">−</button>
        <button class="ha-btn-icon" id="ha-close-btn" title="${t('widget.close')}">×</button>
      </div>
    </div>
  `;
}

function renderNoHotel() {
  panel.innerHTML = renderHeader() + `
    <div class="ha-panel-body">
      <div class="ha-empty">
        <p>${t('widget.no_hotel')}</p>
        <p style="font-size:12px;color:#999;margin-top:8px;">
          ${t('widget.no_hotel_hint')}
        </p>
      </div>
    </div>
  `;
  bindHeaderEvents();
}

async function renderIdle() {
  const adapter = await getAdapter();
  const ctx = adapter ? await adapter.getReview() : null;
  const review = ctx?.content || '';
  console.log('[AssistantWidget] renderIdle → review from adapter:', review, '(ctx:', ctx, ')');
  
  panel.innerHTML = renderHeader() + `
    <div class="ha-panel-body">
      <div class="ha-hotel-badge">
        ✨ ${t('widget.title')}
      </div>
      <div class="ha-review-box" id="ha-review-text">
        ${review || `<span class="ha-placeholder">${t('widget.review_placeholder')}</span>`}
      </div>
      <button class="ha-btn ha-btn-primary" id="ha-generate-btn">${t('widget.generate')}</button>
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
        <span class="ha-status-text" id="ha-status-text">${t('widget.generating')}</span>
      </div>
      <div class="ha-reply-box streaming" id="ha-reply-box">
        <span class="ha-placeholder">${t('widget.waiting')}</span>
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
        <span class="ha-status-text">${t('widget.reply_generated')}</span>
      </div>
      ${review ? `<div class="ha-review-box"><strong>${t('widget.review_label')}</strong>${review}</div>` : ''}
      <div class="ha-reply-box" id="ha-reply-box">${reply || t('widget.empty_reply')}</div>
      <div class="ha-actions">
        <button class="ha-btn ha-btn-secondary" id="ha-edit-btn">${t('widget.edit_reply')}</button>
        <button class="ha-btn ha-btn-primary" id="ha-copy-btn">${t('widget.copy')}</button>
      </div>
      <button class="ha-btn ha-btn-text" id="ha-retry-btn">${t('widget.regenerate')}</button>
    </div>
  `;
  bindHeaderEvents();
  document.getElementById('ha-edit-btn').addEventListener('click', () => setPanelView('editing'));
  document.getElementById('ha-copy-btn').addEventListener('click', onCopy);
  document.getElementById('ha-retry-btn').addEventListener('click', onGenerate);
}


function renderError() {
  const error = store.getError() || t('widget.unknown_error');

  panel.innerHTML = renderHeader() + `
    <div class="ha-panel-body">
      <div class="ha-status-bar error">
        <span class="ha-status-dot"></span>
        <span class="ha-status-text">${t('widget.operation_failed')}</span>
      </div>
      <div class="ha-error-box">${error}</div>
      <button class="ha-btn ha-btn-primary" id="ha-retry-btn">${t('widget.retry')}</button>
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
        <span class="ha-status-text">${t('widget.editing_reply')}</span>
      </div>
      <textarea class="ha-edit-textarea" id="ha-edit-textarea" rows="6">${reply}</textarea>
      <div class="ha-actions">
        <button class="ha-btn ha-btn-secondary" id="ha-edit-cancel-btn">${t('widget.edit_cancel')}</button>
        <button class="ha-btn ha-btn-primary" id="ha-edit-confirm-btn">${t('widget.edit_confirm')}</button>
        <button class="ha-btn ha-btn-primary" id="ha-edit-publish-btn">${t('widget.edit_publish')}</button>
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
  // hotel_context 由 Service Worker 自己从 storage 读取
  // Content Script 只传 review

  const adapter = await getAdapter();
  if (!adapter) {
    updateStatus('error', t('widget.page_not_supported'));
    setPanelView('idle');
    return;
  }

  const ctx = await adapter.getReview();
  const review = ctx?.content ?? '';
  if (!review) {
    updateStatus('error', t('widget.no_review'));
    setPanelView('idle');
    return;
  }

  _currentReview = review;

  // 检查邀请码
  try {
    const inviteResp = await chrome.runtime.sendMessage({ type: 'CHECK_INVITE' }).catch(() => ({ hasInvite: false }));
    if (!inviteResp?.hasInvite) {
      store.setError(t('widget.set_invite_first'));
      setPanelView('error');
      return;
    }
  } catch {
    store.setError(t('widget.set_invite_first'));
    setPanelView('error');
    return;
  }

  store.startRun(null);
  setPanelView('running');
  setFABState('generating');

  // 只发 review，hotel_context 由 Service Worker 自己从 storage 读取
  try {
    if (!chrome.runtime?.id) {
      updateStatus('error', t('widget.ext_refreshed'));
      setPanelView('error');
      return;
    }

    await chrome.runtime.sendMessage({
      type: 'GENERATE_REPLY',
      payload: { review },
    }).catch((e) => {
      console.error('[AssistantWidget] sendMessage rejected:', (e as Error)?.message, e);
      throw e;
    });
  } catch (e) {
    console.error('[AssistantWidget] sendMessage failed:', (e as Error)?.message, e);
    store.setError(t('widget.conn_error'));
    setPanelView('error');
  }
}

async function onCopy() {
  const reply = store.getReply();
  if (!reply) return;

  try {
    await navigator.clipboard.writeText(reply);
    updateStatus('completed', t('widget.copied'));
  } catch {
    // fallback: 使用 textarea 选择复制
    const textarea = document.createElement('textarea');
    textarea.value = reply;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    updateStatus('completed', t('widget.copied'));
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
