/**
 * OTAAdapter 接口定义
 *
 * 每个 OTA 平台实现此接口，负责：
 * 1. matches()     — 页面识别
 * 2. getReview()   — 提取评论上下文
 * 3. fillReply()   — 填充 AI 回复到页面
 * 4. publish()     — 触发发布（MVP 阶段保留接口，不自动发布）
 *
 * Adapter 不负责：AI 调用、酒店配置、workflow 调度。
 */

import type { ReviewContext } from '../../state/review.js';

export interface OTAAdapter {
  /** 平台名称标识 */
  readonly name: string;

  /** 判断当前页面是否属于此 OTA 平台 */
  matches(): boolean;

  /** 从页面提取评论上下文 */
  getReview(): Promise<ReviewContext | null>;

  /** 将 AI 回复文本填充到页面回复框 */
  fillReply(reply: string): Promise<boolean>;

  /** 触发页面发布/提交操作 */
  publish(): Promise<boolean>;
}
