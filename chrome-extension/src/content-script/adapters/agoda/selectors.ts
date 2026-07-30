export const SELECTORS = {
  REVIEW_CONTENT: [
    '.review-text',
    '.comment-content',
    '[data-element-name="review-text"]',
  ] as const,
  RATING: [
    '.rating',
    '.score',
    '[class*="star"]',
  ] as const,
  REPLY_TEXTAREA: [
    'textarea[class*="reply"]',
    'textarea[placeholder*="reply"]',
    'textarea[data-testid*="reply"]',
    '.reply-textarea',
  ] as const,
  PUBLISH_BUTTON: [
    '.submit-btn',
    '[type="submit"]',
    '[data-testid="submit"]',
  ] as const,
} as const;
