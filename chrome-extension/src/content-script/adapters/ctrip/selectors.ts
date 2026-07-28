/**
 * 携程 DOM 选择器
 *
 * 集中管理，便于携程 DOM 结构变化时快速维护。
 * 携程评论页常见域名：hotels.ctrip.com, YOU.ctrip.com
 */

export const SELECTORS = {
  /** 评论内容容器 */
  REVIEW_CONTENT: [
    '.comment-content',
    '.review-content',
    '.J-comment',
  ] as const,

  /** 评分元素（在评论卡片内查找） */
  RATING: [
    '.rating',
    '.score',
    '[class*="rating"]',
  ] as const,

  /** 回复输入框 */
  REPLY_TEXTAREA: [
    'textarea[class*="reply"]',
    'textarea[placeholder*="回复"]',
    'textarea[placeholder*="评价"]',
    '.reply-textarea',
  ] as const,

  /** 发布/提交按钮 */
  PUBLISH_BUTTON: [
    '.submit-btn',
    '.send-btn',
    'button[type="submit"]',
    '[class*="submit"]',
    '[class*="send"]',
  ] as const,
} as const;
