/**
 * InviteCodeService — 邀请码管理
 *
 * 独立于 HotelConfigService，邀请码单独存于 chrome.storage.local。
 * 提供邀请码的保存、读取、验证功能。
 */

import { ChromeStorage } from '../storage/chrome_storage.js';

const STORAGE_KEY = 'invite_code';

export class InviteCodeService {
  private storage = new ChromeStorage();

  /**
   * 获取已保存的邀请码
   */
  async get(): Promise<string | null> {
    return this.storage.get<string>(STORAGE_KEY);
  }

  /**
   * 保存邀请码
   */
  async set(code: string): Promise<void> {
    await this.storage.set(STORAGE_KEY, code);
  }

  /**
   * 清除邀请码
   */
  async remove(): Promise<void> {
    await this.storage.remove(STORAGE_KEY);
  }

  /**
   * 验证邀请码是否有效（调后端 /api/invite/validate）
   */
  async validate(code: string): Promise<{ valid: boolean; message?: string }> {
    try {
      const apiUrl = await this._getApiUrl();
      const resp = await fetch(`${apiUrl}/api/invite/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      });

      if (resp.status === 404) {
        return { valid: false, message: '邀请码不存在' };
      }
      if (resp.status === 410) {
        return { valid: false, message: '邀请码已过期' };
      }
      if (!resp.ok) {
        return { valid: false, message: '验证失败' };
      }

      const data = await resp.json();
      return { valid: data.valid ?? true };
    } catch {
      return { valid: false, message: '无法连接服务器' };
    }
  }

  /**
   * 检查当前保存的邀请码是否仍有效
   */
  async checkCurrent(): Promise<{ valid: boolean; message?: string }> {
    const code = await this.get();
    if (!code) {
      return { valid: false, message: '未设置邀请码' };
    }
    return this.validate(code);
  }

  /**
   * 获取后端 API 地址
   */
  private async _getApiUrl(): Promise<string> {
    try {
      const resp = await chrome.runtime.sendMessage({ type: 'GET_API_URL' });
      return resp?.apiUrl || 'http://localhost:8000';
    } catch {
      return 'http://localhost:8000';
    }
  }
}

/** 单例 */
export const inviteCodeService = new InviteCodeService();
