/**
 * IHotelConfigRepository — 酒店配置 Repository 接口
 *
 * 抽象配置来源：
 * - LocalRepository     → chrome.storage.local（当前阶段）
 * - RemoteRepository    → 后端 API（未来阶段）
 *
 * 业务代码只依赖此接口，不关心具体存储实现。
 */

import type { HotelConfig, ReplySettings } from './models.js';

export interface IHotelConfigRepository {
  /** 列出所有酒店 */
  list(): Promise<HotelConfig[]>;

  /** 按 ID 查找酒店 */
  findById(id: string): Promise<HotelConfig | null>;

  /** 保存酒店（创建或覆盖） */
  save(hotel: HotelConfig): Promise<void>;

  /** 删除酒店 */
  delete(id: string): Promise<void>;

  /** 更新回复设置 */
  updateReplySettings(id: string, settings: ReplySettings): Promise<void>;
}
