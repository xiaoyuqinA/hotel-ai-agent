/**
 * ReviewContext — 评论上下文领域类型
 *
 * 跨模块共享：content script → background → backend workflow。
 * Adapter 负责从 OTA 页面提取此结构，workflow 消费此结构。
 */

export interface ReviewContext {
  /** OTA 平台标识 */
  platform: 'ctrip' | 'fliggy' | 'booking' | 'agoda' | 'expedia';
  /** 酒店 ID（页面中可提取时） */
  hotelId?: string;
  /** 评论 ID */
  reviewId?: string;
  /** 评论正文 */
  content: string;
  /** 评分（如 4.5） */
  rating?: number;
}
