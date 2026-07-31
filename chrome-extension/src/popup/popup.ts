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
import { DEFAULT_REPLY_SETTINGS } from '../config/models.js';

// ── Service ───────────────────────────────────────────────────────────────────

const configService = new HotelConfigService(new LocalHotelConfigRepository());

// ── DOM ───────────────────────────────────────────────────────────────────────

let contentEl: HTMLElement;

async function render() {
  contentEl = document.getElementById('app-content')!;

  // 1. 检查邀请码
  const inviteCode = await inviteCodeService.get();
  if (!inviteCode) {
    return renderInviteCode();
  }

  // 2. 检查酒店
  const current = await configService.getCurrentHotel();
  if (!current) {
    return renderCreateHotel();
  }

  return renderHotelHome(current);
}

// ── 视图 0：邀请码 ─────────────────────────────────────────────────────────

function renderInviteCode() {
  contentEl.innerHTML = `
    <div class="section">
      <div class="label">🔑 邀请码</div>
      <p style="font-size:13px;color:#666;margin-bottom:12px;">
        请输入商家邀请码开始使用
      </p>
      <input class="input" id="invite-code-input"
             placeholder="INVITE-XXXX"
             style="margin-bottom:8px;" />
      <button class="btn btn-primary" id="verify-invite-btn">验证</button>
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
    showStatus('invite-status', '请输入邀请码', 'error');
    return;
  }

  showStatus('invite-status', '验证中...', '');
  const btn = document.getElementById('verify-invite-btn') as HTMLButtonElement;
  btn.disabled = true;
  btn.textContent = '验证中';

  try {
    const result = await inviteCodeService.validate(code);
    if (result.valid) {
      await inviteCodeService.set(code);
      await render();
    } else {
      showStatus('invite-status', result.message || '邀请码无效', 'error');
      btn.disabled = false;
      btn.textContent = '验证';
    }
  } catch {
    showStatus('invite-status', '验证失败，请稍后重试', 'error');
    btn.disabled = false;
    btn.textContent = '验证';
  }
}

// ── 视图 1：创建酒店 ─────────────────────────────────────────────────────────

function renderCreateHotel(errorMsg?: string) {
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

  document.getElementById('create-hotel-btn')!.addEventListener('click', onCreateHotel);
}

async function onCreateHotel() {
  const nameInput = document.getElementById('hotel-name-input') as HTMLInputElement;
  const cityInput = document.getElementById('hotel-city-input') as HTMLInputElement;
  const name = nameInput.value.trim();
  const city = cityInput.value.trim();

  if (!name) {
    showStatus('create-status', '请输入酒店名称', 'error');
    return;
  }
  if (!city) {
    showStatus('create-status', '请输入所在城市', 'error');
    return;
  }

  const btn = document.getElementById('create-hotel-btn') as HTMLButtonElement;
  btn.disabled = true;
  btn.textContent = '创建中...';

  try {
    const hotel = await configService.createHotel({ name, city });
    await configService.setCurrentHotel({
      hotel_id: hotel.id,
      hotel_name: hotel.name,
    });
    await render();
  } catch (e) {
    showStatus('create-status', '创建失败：' + (e as Error).message, 'error');
    btn.disabled = false;
    btn.textContent = '创建酒店';
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

    <div class="section" id="invite-code-section">
      <div class="label">🔑 邀请码</div>
      <div style="display:flex;align-items:center;gap:8px;margin-top:4px;">
        <span id="invite-code-text" style="font-size:13px;color:#999;">加载中...</span>
        <button class="btn btn-secondary" id="change-invite-btn"
                style="width:auto;padding:4px 10px;font-size:12px;">更换</button>
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
  el.textContent = code || '未设置';
}

function renderInviteCodeInput() {
  contentEl.innerHTML = `
    <div class="section">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
        <button class="btn btn-secondary" id="back-btn"
                style="width:auto;padding:6px 14px;font-size:13px;">← 返回</button>
        <span style="font-weight:500;">修改邀请码</span>
      </div>
    </div>
    <div class="section">
      <div class="label">邀请码</div>
      <input class="input" id="edit-invite-input"
             placeholder="输入新邀请码"
             style="margin-bottom:12px;" />
      <div class="btn-row">
        <button class="btn btn-secondary" id="cancel-invite-btn">取消</button>
        <button class="btn btn-primary" id="save-invite-btn">保存</button>
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
    showStatus('edit-invite-status', '请输入邀请码', 'error');
    return;
  }

  const btn = document.getElementById('save-invite-btn') as HTMLButtonElement;
  btn.disabled = true;
  btn.textContent = '验证中...';

  try {
    const result = await inviteCodeService.validate(code);
    if (result.valid) {
      await inviteCodeService.set(code);
      showStatus('edit-invite-status', '✅ 邀请码已更新', 'success');
      setTimeout(() => render(), 1200);
    } else {
      showStatus('edit-invite-status', result.message || '邀请码无效', 'error');
      btn.disabled = false;
      btn.textContent = '保存';
    }
  } catch {
    showStatus('edit-invite-status', '验证失败', 'error');
    btn.disabled = false;
    btn.textContent = '保存';
  }
}

async function loadSettingsPreview(hotelId: string) {
  const container = document.getElementById('settings-preview')!;
  try {
    const hotel = await configService.getHotel(hotelId);
    const settings = hotel?.reply_settings ?? DEFAULT_REPLY_SETTINGS;
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
          ${(settings.rules || []).map((r: string) => '• ' + r).join('<br>') || '无'}
        </div>
      </div>
    `;
  } catch (e) {
    container.innerHTML = `
      <div class="label">回复配置</div>
      <div class="status-text error">加载失败：${(e as Error).message}</div>
    `;
  }
}

// ── 视图 3：编辑设置 ─────────────────────────────────────────────────────────

async function renderEditSettings(current: CurrentHotel) {
  contentEl.innerHTML = `
    <div class="section">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
        <button class="btn btn-secondary" id="back-btn"
                style="width:auto;padding:6px 14px;font-size:13px;">← 返回</button>
        <span style="font-weight:500;">${current.hotel_name}</span>
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

  // 加载当前设置
  try {
    const hotel = await configService.getHotel(current.hotel_id);
    const settings = hotel?.reply_settings ?? DEFAULT_REPLY_SETTINGS;
    (document.getElementById('edit-tone') as HTMLInputElement).value = settings.tone || '';
    (document.getElementById('edit-style') as HTMLInputElement).value = settings.style || '';
    (document.getElementById('edit-rules') as HTMLTextAreaElement).value = (settings.rules || []).join('\n');
  } catch (e) {
    showStatus('edit-status', '加载失败：' + (e as Error).message, 'error');
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
    showStatus('edit-status', '回复语气不能为空', 'error');
    return;
  }

  const btn = document.getElementById('save-settings-btn') as HTMLButtonElement;
  btn.disabled = true;
  btn.textContent = '保存中...';

  try {
    await configService.updateReplySettings(current.hotel_id, { tone, style, rules });
    showStatus('edit-status', '✅ 设置已保存', 'success');
    setTimeout(() => render(), 1200);
  } catch (e) {
    showStatus('edit-status', '保存失败：' + (e as Error).message, 'error');
    btn.disabled = false;
    btn.textContent = '保存设置';
  }
}

// ── 酒店列表弹窗 ─────────────────────────────────────────────────────────────

async function onShowHotelList() {
  const modal = document.getElementById('hotel-list-modal')!;
  const hotels = await configService.listHotels();
  const current = await configService.getCurrentHotel();

  modal.innerHTML = `
    <div class="modal-content">
      <h3>选择酒店</h3>
      ${hotels.map(h => `
        <div class="modal-hotel-item" data-id="${h.id}" data-name="${h.name}">
          <div class="m-name">${h.name} ${current && current.hotel_id === h.id ? '✓' : ''}</div>
          <div class="m-id">${h.id}</div>
        </div>
      `).join('')}
      <div class="modal-new-hotel" id="modal-new-hotel-btn">+ 创建新酒店</div>
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

function showStatus(id: string, msg: string, type: 'error' | 'success' | 'hidden') {
  const el = document.getElementById(id)!;
  el.textContent = msg;
  el.className = `status-text ${type}`;
}

document.addEventListener('DOMContentLoaded', render);
