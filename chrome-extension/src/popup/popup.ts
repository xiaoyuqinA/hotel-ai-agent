/**
 * Popup Script — 三视图路由
 *
 * 视图 1：创建酒店（首次使用 / 主动创建）
 * 视图 2：酒店首页（现有酒店，展示配置概览）
 * 视图 3：编辑设置（ReplySettings 编辑）
 *
 * 全部配置通过 HotelConfigService 操作，
 * 不再直接读写 chrome.storage 或调用后端 API。
 */

import { LocalHotelConfigRepository } from '../config/local_repository.js';
import { HotelConfigService } from '../config/service.js';
import { inviteCodeService } from '../config/invite_service.js';
import type { CurrentHotel, HotelConfig, ReplySettings } from '../config/models.js';
import { getDefaultReplySettings } from '../config/models.js';
import { initI18n, setLang, getCurrentLang, t, type Lang } from '../i18n/index.js';

// ── Service ───────────────────────────────────────────────────────────────────

const configService = new HotelConfigService(new LocalHotelConfigRepository());

// ── DOM ───────────────────────────────────────────────────────────────────────

let contentEl: HTMLElement;

async function render() {
  contentEl = document.getElementById('app-content')!;

  // 初始化语言（当前语言 -> 渲染文案）
  await initI18n();
  // 更新文档标题与 header（静态占位由 JS 注入）
  document.title = t('app.title');
  const header = document.querySelector('.header');
  if (header) {
    header.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;">
        <div>
          <h1>✦ ${t('app.title')}</h1>
          <p>${t('app.subtitle')}</p>
        </div>
        <button id="lang-switch-btn"
                style="background:rgba(255,255,255,0.18);border:none;border-radius:6px;color:white;padding:4px 8px;font-size:12px;cursor:pointer;">
          ${t('lang.switch')}
        </button>
      </div>
    `;
    document.getElementById('lang-switch-btn')!.addEventListener('click', onToggleLang);
  }

  // 1. 检查邀请码
  const inviteCode = await inviteCodeService.get();
  if (!inviteCode) {
    return renderInviteCode();
  }

  // 2. 有邀请码 → 走原有酒店逻辑
  const current = await configService.getCurrentHotel();
  if (!current) {
    return renderCreateHotel();
  }

  return renderHotelHome(current);
}

/** 切换中/英语言并重渲染 */
async function onToggleLang() {
  const next: Lang = getCurrentLang() === 'zh' ? 'en' : 'zh';
  await setLang(next);
  await render();
}

// ── 视图 0：邀请码 ─────────────────────────────────────────────────────────

function renderInviteCode() {
  contentEl.innerHTML = `
    <div class="section">
      <div class="label">${t('invite.label')}</div>
      <p style="font-size:13px;color:#666;margin-bottom:12px;">
        ${t('invite.hint')}
      </p>
      <input class="input" id="invite-code-input"
             placeholder="${t('invite.placeholder')}"
             style="margin-bottom:8px;" />
      <button class="btn btn-primary" id="verify-invite-btn">${t('invite.verify')}</button>
      <div id="invite-status" class="status-text"></div>
    </div>
  `;

  document.getElementById('verify-invite-btn')!.addEventListener('click', onVerifyInvite);
  document.getElementById('invite-code-input')!.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') onVerifyInvite();
  });
  document.getElementById('invite-code-input')!.focus();
}

async function onVerifyInvite() {
  const input = document.getElementById('invite-code-input') as HTMLInputElement;
  const code = input.value.trim();
  if (!code) {
    showStatus('invite-status', t('invite.required'), 'error');
    return;
  }

  showStatus('invite-status', t('invite.verifying'), '');
  const btn = document.getElementById('verify-invite-btn') as HTMLButtonElement;
  btn.disabled = true;
  btn.textContent = t('invite.verifying');

  try {
    const result = await inviteCodeService.validate(code);
    if (result.valid) {
      await inviteCodeService.set(code);
      await render();
    } else {
      showStatus('invite-status', inviteErrorMessage(result), 'error');
      btn.disabled = false;
      btn.textContent = t('invite.verify');
    }
  } catch {
    showStatus('invite-status', t('invite.verify_failed_retry'), 'error');
    btn.disabled = false;
    btn.textContent = t('invite.verify');
  }
}

// ── 视图 1：创建酒店 ─────────────────────────────────────────────────────────

function renderCreateHotel(errorMsg?: string) {
  contentEl.innerHTML = `
    <div class="section">
      <div class="label">${t('create.welcome')}</div>
      <p style="font-size:13px;color:#666;margin-bottom:12px;">
        ${t('create.hint')}
      </p>
      <input class="input" id="hotel-name-input"
             placeholder="${t('create.name_placeholder')}"
             style="margin-bottom:8px;" />
      <input class="input" id="hotel-city-input"
             placeholder="${t('create.city_placeholder')}"
             style="margin-bottom:12px;" />
      <button class="btn btn-primary" id="create-hotel-btn">${t('create.submit')}</button>
      <button class="btn btn-secondary" id="skip-hotel-btn"
              style="margin-top:8px;">${t('create.skip')}</button>
      <div id="create-status" class="status-text ${errorMsg ? 'error' : ''}">
        ${errorMsg || ''}
      </div>
    </div>
  `;

  document.getElementById('create-hotel-btn')!.addEventListener('click', onCreateHotel);
  document.getElementById('skip-hotel-btn')!.addEventListener('click', () => window.close());
}

async function onCreateHotel() {
  const nameInput = document.getElementById('hotel-name-input') as HTMLInputElement;
  const cityInput = document.getElementById('hotel-city-input') as HTMLInputElement;
  const name = nameInput.value.trim();
  const city = cityInput.value.trim();

  if (!name) {
    showStatus('create-status', t('create.name_required'), 'error');
    return;
  }
  if (!city) {
    showStatus('create-status', t('create.city_required'), 'error');
    return;
  }

  const btn = document.getElementById('create-hotel-btn') as HTMLButtonElement;
  btn.disabled = true;
  btn.textContent = t('create.creating');

  try {
    const hotel = await configService.createHotel({ name, city });
    await configService.setCurrentHotel({
      hotel_id: hotel.id,
      hotel_name: hotel.name,
    });
    await render();
  } catch (e) {
    showStatus('create-status', t('create.failed') + (e as Error).message, 'error');
    btn.disabled = false;
    btn.textContent = t('create.submit');
  }
}

// ── 视图 2：酒店首页 ─────────────────────────────────────────────────────────

async function renderHotelHome(current: CurrentHotel) {
  contentEl.innerHTML = `
    <div class="section">
      <div class="hotel-selector" id="hotel-selector-btn">
        <span class="icon">🏨</span>
        <span class="name">${current.hotel_name}</span>
        <span class="arrow">▼</span>
      </div>
    </div>

    <div class="section" id="settings-preview">
      <div class="label">${t('home.reply_config')}</div>
      <div style="text-align:center;padding:20px;color:#999;font-size:13px;">
        ${t('home.loading')}
      </div>
    </div>

    <div class="section">
      <button class="settings-btn" id="edit-settings-btn">
        ${t('home.edit_settings')}
      </button>
    </div>

    <div class="section" id="invite-code-section">
      <div class="label">${t('invite.label')}</div>
      <div style="display:flex;align-items:center;gap:8px;margin-top:4px;">
        <span id="invite-code-text" style="font-size:13px;color:#999;">${t('home.loading')}</span>
        <button class="btn btn-secondary" id="change-invite-btn"
                style="width:auto;padding:4px 10px;font-size:12px;">${t('invite.change')}</button>
      </div>
    </div>
  `;

  loadSettingsPreview(current.hotel_id);
  loadInviteCode();

  document.getElementById('hotel-selector-btn')!.addEventListener('click', onShowHotelList);
  document.getElementById('edit-settings-btn')!.addEventListener('click', () => renderEditSettings(current));
  document.getElementById('change-invite-btn')!.addEventListener('click', renderInviteCodeInput);
}

async function loadInviteCode() {
  const el = document.getElementById('invite-code-text');
  if (!el) return;
  const code = await inviteCodeService.get();
  el.textContent = code || t('invite.not_set');
}

function renderInviteCodeInput() {
  contentEl.innerHTML = `
    <div class="section">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
        <button class="btn btn-secondary" id="back-btn"
                style="width:auto;padding:6px 14px;font-size:13px;">${t('edit.back')}</button>
        <span style="font-weight:500;">${t('invite.edit_title')}</span>
      </div>
    </div>
    <div class="section">
      <div class="label">${t('invite.label')}</div>
      <input class="input" id="edit-invite-input"
             placeholder="${t('invite.new_placeholder')}"
             style="margin-bottom:12px;" />
      <div class="btn-row">
        <button class="btn btn-secondary" id="cancel-invite-btn">${t('invite.cancel')}</button>
        <button class="btn btn-primary" id="save-invite-btn">${t('invite.save')}</button>
      </div>
      <div id="edit-invite-status" class="status-text hidden"></div>
    </div>
  `;

  document.getElementById('back-btn')!.addEventListener('click', () => render());
  document.getElementById('cancel-invite-btn')!.addEventListener('click', () => render());
  document.getElementById('save-invite-btn')!.addEventListener('click', onSaveInviteCode);
}

async function onSaveInviteCode() {
  const input = document.getElementById('edit-invite-input') as HTMLInputElement;
  const code = input.value.trim();
  if (!code) {
    showStatus('edit-invite-status', t('invite.required'), 'error');
    return;
  }

  const btn = document.getElementById('save-invite-btn') as HTMLButtonElement;
  btn.disabled = true;
  btn.textContent = t('invite.verifying');

  try {
    const result = await inviteCodeService.validate(code);
    if (result.valid) {
      await inviteCodeService.set(code);
      showStatus('edit-invite-status', t('invite.updated'), 'success');
      setTimeout(() => render(), 1200);
    } else {
      showStatus('edit-invite-status', inviteErrorMessage(result), 'error');
      btn.disabled = false;
      btn.textContent = t('invite.save');
    }
  } catch {
    showStatus('edit-invite-status', t('invite.validate_failed'), 'error');
    btn.disabled = false;
    btn.textContent = t('invite.save');
  }
}

async function loadSettingsPreview(hotelId: string) {
  const container = document.getElementById('settings-preview')!;
  try {
    const hotel = await configService.getHotel(hotelId);
    const settings = hotel?.reply_settings ?? getDefaultReplySettings(getCurrentLang());
    container.innerHTML = `
      <div class="label">${t('home.reply_config')}</div>
      <div class="config-item">
        <div class="config-label">${t('home.tone')}</div>
        <div class="config-value">${settings.tone || t('home.unset')}</div>
      </div>
      <div class="config-item">
        <div class="config-label">${t('home.style')}</div>
        <div class="config-value">${settings.style || t('home.unset')}</div>
      </div>
      <div class="config-item">
        <div class="config-label">${t('home.rules')}</div>
        <div class="config-value">
          ${(settings.rules || []).map((r: string) => '• ' + r).join('<br>') || t('home.none')}
        </div>
      </div>
    `;
  } catch (e) {
    container.innerHTML = `
      <div class="label">${t('home.reply_config')}</div>
      <div class="status-text error">${t('status.load_failed')}${(e as Error).message}</div>
    `;
  }
}

// ── 视图 3：编辑设置 ─────────────────────────────────────────────────────────

async function renderEditSettings(current: CurrentHotel) {
  contentEl.innerHTML = `
    <div class="section">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
        <button class="btn btn-secondary" id="back-btn"
                style="width:auto;padding:6px 14px;font-size:13px;">${t('edit.back')}</button>
        <span style="font-weight:500;">${current.hotel_name}</span>
      </div>
    </div>

    <div class="section">
      <div class="label">${t('home.tone')}</div>
      <input class="input" id="edit-tone" placeholder="${t('edit.tone_placeholder')}"
             style="margin-bottom:10px;" />
      <div class="label">${t('home.style')}</div>
      <input class="input" id="edit-style" placeholder="${t('edit.style_placeholder')}"
             style="margin-bottom:10px;" />
      <div class="label">${t('edit.rules_label')}</div>
      <textarea class="textarea" id="edit-rules" rows="4"
                placeholder="${t('edit.rules_placeholder')}"></textarea>

      <div class="btn-row">
        <button class="btn btn-secondary" id="cancel-edit-btn">${t('edit.cancel')}</button>
        <button class="btn btn-primary" id="save-settings-btn">${t('edit.save')}</button>
      </div>
      <div id="edit-status" class="status-text hidden"></div>
    </div>
  `;

  // 加载当前设置
  try {
    const hotel = await configService.getHotel(current.hotel_id);
    const settings = hotel?.reply_settings ?? getDefaultReplySettings(getCurrentLang());
    (document.getElementById('edit-tone') as HTMLInputElement).value = settings.tone || '';
    (document.getElementById('edit-style') as HTMLInputElement).value = settings.style || '';
    (document.getElementById('edit-rules') as HTMLTextAreaElement).value = (settings.rules || []).join('\n');
  } catch (e) {
    showStatus('edit-status', t('edit.load_failed') + (e as Error).message, 'error');
  }

  document.getElementById('back-btn')!.addEventListener('click', () => render());
  document.getElementById('cancel-edit-btn')!.addEventListener('click', () => render());
  document.getElementById('save-settings-btn')!.addEventListener('click', () => onSaveSettings(current));
}

async function onSaveSettings(current: CurrentHotel) {
  const tone = (document.getElementById('edit-tone') as HTMLInputElement).value.trim();
  const style = (document.getElementById('edit-style') as HTMLInputElement).value.trim();
  const rulesRaw = (document.getElementById('edit-rules') as HTMLTextAreaElement).value.trim();
  const rules = rulesRaw ? rulesRaw.split('\n').map(r => r.trim()).filter(Boolean) : [];

  if (!tone) {
    showStatus('edit-status', t('edit.tone_required'), 'error');
    return;
  }

  const btn = document.getElementById('save-settings-btn') as HTMLButtonElement;
  btn.disabled = true;
  btn.textContent = t('edit.saving');

  try {
    await configService.updateReplySettings(current.hotel_id, { tone, style, rules });
    showStatus('edit-status', t('edit.saved'), 'success');
    setTimeout(() => render(), 1200);
  } catch (e) {
    showStatus('edit-status', t('edit.save_failed') + (e as Error).message, 'error');
    btn.disabled = false;
    btn.textContent = t('edit.save');
  }
}

// ── 酒店列表弹窗 ─────────────────────────────────────────────────────────────

async function onShowHotelList() {
  const modal = document.getElementById('hotel-list-modal')!;
  const hotels = await configService.listHotels();
  const current = await configService.getCurrentHotel();

  modal.innerHTML = `
    <div class="modal-content">
      <h3>${t('modal.select_hotel')}</h3>
      ${hotels.map(h => `
        <div class="modal-hotel-item" data-id="${h.id}" data-name="${h.name}">
          <div class="m-name">${h.name} ${current && current.hotel_id === h.id ? '✓' : ''}</div>
          <div class="m-id">${h.id}</div>
        </div>
      `).join('')}
      <div class="modal-new-hotel" id="modal-new-hotel-btn">${t('modal.new_hotel')}</div>
    </div>
  `;

  modal.querySelectorAll('.modal-hotel-item').forEach(el => {
    el.addEventListener('click', async () => {
      await configService.setCurrentHotel({
        hotel_id: (el as HTMLElement).dataset.id!,
        hotel_name: (el as HTMLElement).dataset.name!,
      });
      modal.classList.add('hidden');
      await render();
    });
  });

  document.getElementById('modal-new-hotel-btn')!.addEventListener('click', async () => {
    await configService.clearCurrentHotel();
    modal.classList.add('hidden');
    renderCreateHotel();
  });

  modal.classList.remove('hidden');
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.add('hidden');
  });
}

// ── 通用 ──────────────────────────────────────────────────────────────────────

/** 将邀请码验证的错误码映射为当前语言的提示文案 */
function inviteErrorMessage(result: { errorCode?: string; message?: string }): string {
  switch (result.errorCode) {
    case 'not_exist': return t('invite.not_exist');
    case 'expired': return t('invite.expired');
    case 'validate_failed': return t('invite.validate_failed');
    case 'conn_failed': return t('invite.conn_failed');
    default: return result.message || t('invite.invalid');
  }
}

function showStatus(id: string, msg: string, type: 'error' | 'success' | 'hidden') {
  const el = document.getElementById(id)!;
  el.textContent = msg;
  el.className = `status-text ${type}`;
}

document.addEventListener('DOMContentLoaded', render);
