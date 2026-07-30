/**
 * LocalHotelConfigRepository — 本地酒店配置存储
 *
 * 基于 Chrome Storage 的 Repository 实现。
 * 当前阶段所有酒店配置存储在 chrome.storage.local 中。
 *
 * 存储结构：
 *   key: 'hotel_configs'
 *   value: HotelConfig[]
 *
 *   key: 'current_hotel'
 *   value: CurrentHotel
 */

import { ChromeStorage } from '../storage/chrome_storage.js';
import type { HotelConfig, ReplySettings } from './models.js';
import type { IHotelConfigRepository } from './repository.js';

const STORAGE_KEY = 'hotel_configs';

export class LocalHotelConfigRepository implements IHotelConfigRepository {
  private storage = new ChromeStorage();

  /**
   * 列出所有酒店
   */
  async list(): Promise<HotelConfig[]> {
    const hotels = await this.storage.get<HotelConfig[]>(STORAGE_KEY);
    return hotels ?? [];
  }

  /**
   * 按 ID 查找酒店
   */
  async findById(id: string): Promise<HotelConfig | null> {
    const hotels = await this.list();
    return hotels.find((h) => h.id === id) ?? null;
  }

  /**
   * 保存酒店（创建或更新）
   */
  async save(hotel: HotelConfig): Promise<void> {
    const hotels = await this.list();
    const index = hotels.findIndex((h) => h.id === hotel.id);

    if (index >= 0) {
      hotels[index] = hotel;
    } else {
      hotels.push(hotel);
    }

    await this.storage.set(STORAGE_KEY, hotels);
  }

  /**
   * 删除酒店
   */
  async delete(id: string): Promise<void> {
    const hotels = await this.list();
    const filtered = hotels.filter((h) => h.id !== id);
    await this.storage.set(STORAGE_KEY, filtered);
  }

  /**
   * 更新回复设置
   */
  async updateReplySettings(id: string, settings: ReplySettings): Promise<void> {
    const hotels = await this.list();
    const index = hotels.findIndex((h) => h.id === id);

    if (index < 0) {
      throw new Error(`Hotel not found: ${id}`);
    }

    hotels[index] = {
      ...hotels[index],
      reply_settings: settings,
      updated_at: Date.now(),
    };

    await this.storage.set(STORAGE_KEY, hotels);
  }
}
