/**
 * HotelConfigService — 酒店配置业务服务
 *
 * 职责：
 * 1. 创建酒店（生成 ID、时间戳等）
 * 2. 查询/更新酒店配置
 * 3. 管理当前选中酒店
 *
 * 通过 IHotelConfigRepository 接口隔离存储实现。
 * 当前阶段使用 LocalHotelConfigRepository，未来可切换为远程 Repository。
 */

import type { IHotelConfigRepository } from './repository.js';
import type { CreateHotelInput, CurrentHotel, HotelConfig, ReplySettings } from './models.js';
import { DEFAULT_REPLY_SETTINGS } from './models.js';
import { ChromeStorage } from '../storage/chrome_storage.js';

const CURRENT_HOTEL_KEY = 'current_hotel';

export class HotelConfigService {
  constructor(private repository: IHotelConfigRepository) {}

  // ── 酒店 CRUD ─────────────────────────────────────────────────────────────────

  /**
   * 创建酒店（生成 ID + 时间戳）
   */
  async createHotel(input: CreateHotelInput): Promise<HotelConfig> {
    const now = Date.now();
    const hotel: HotelConfig = {
      id: `hotel_${now}`,
      name: input.name,
      city: input.city,
      reply_settings: {
        tone: input.reply_settings?.tone ?? DEFAULT_REPLY_SETTINGS.tone,
        style: input.reply_settings?.style ?? DEFAULT_REPLY_SETTINGS.style,
        rules: input.reply_settings?.rules ?? [...DEFAULT_REPLY_SETTINGS.rules],
      },
      created_at: now,
      updated_at: now,
    };

    await this.repository.save(hotel);
    return hotel;
  }

  /**
   * 获取酒店配置
   */
  async getHotel(id: string): Promise<HotelConfig | null> {
    return this.repository.findById(id);
  }

  /**
   * 列出所有酒店
   */
  async listHotels(): Promise<HotelConfig[]> {
    return this.repository.list();
  }

  /**
   * 更新回复设置
   */
  async updateReplySettings(id: string, settings: ReplySettings): Promise<void> {
    await this.repository.updateReplySettings(id, settings);
  }

  /**
   * 删除酒店
   */
  async deleteHotel(id: string): Promise<void> {
    await this.repository.delete(id);
    // 如果删除的是当前酒店，清除 current_hotel
    const current = await this.getCurrentHotel();
    if (current?.hotel_id === id) {
      await this.clearCurrentHotel();
    }
  }

  // ── 当前选中酒店管理 ─────────────────────────────────────────────────────────

  /**
   * 获取当前选中酒店
   */
  async getCurrentHotel(): Promise<CurrentHotel | null> {
    const storage = new ChromeStorage();
    return storage.get<CurrentHotel>(CURRENT_HOTEL_KEY);
  }

  /**
   * 设置当前选中酒店
   */
  async setCurrentHotel(hotel: CurrentHotel): Promise<void> {
    const storage = new ChromeStorage();
    await storage.set(CURRENT_HOTEL_KEY, hotel);
  }

  /**
   * 清除当前选中酒店
   */
  async clearCurrentHotel(): Promise<void> {
    const storage = new ChromeStorage();
    await storage.remove(CURRENT_HOTEL_KEY);
  }

  // ── 便利方法 ──────────────────────────────────────────────────────────────────

  /**
   * 获取当前酒店的 ReplySettings
   * 如果未设置酒店，返回默认设置
   */
  async getCurrentReplySettings(): Promise<ReplySettings> {
    const current = await this.getCurrentHotel();
    if (!current) return { ...DEFAULT_REPLY_SETTINGS };

    const hotel = await this.getHotel(current.hotel_id);
    return hotel?.reply_settings ?? { ...DEFAULT_REPLY_SETTINGS };
  }

  /**
   * 更新当前酒店的回复设置
   */
  async updateCurrentReplySettings(settings: ReplySettings): Promise<void> {
    const current = await this.getCurrentHotel();
    if (!current) throw new Error('No current hotel selected');

    await this.updateReplySettings(current.hotel_id, settings);
  }
}
