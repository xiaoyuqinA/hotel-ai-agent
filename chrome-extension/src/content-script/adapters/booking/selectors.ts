export const SELECTORS = {
  REVIEW_CONTENT: [
    '.review-text',
    '.c-review-block',
    '[data-review-id] .c-review',
  ] as const,
  RATING: [
    '.bui-review-summary__rating',
    '.review-score-badge',
    '[data-testid="rating"]',
  ] as const,
  REPLY_TEXTAREA: [
    'textarea[class*="reply"]',
    'textarea[placeholder*="reply"]',
    'textarea[data-something*="reply"]',
    '.reply-textarea',
  ] as const,
  PUBLISH_BUTTON: [
    '.submit-button',
    '[type="submit"]',
    '[data-testid="submit"]',
  ] as const,
} as const;
