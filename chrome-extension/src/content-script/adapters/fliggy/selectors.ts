export const SELECTORS = {
  REVIEW_CONTENT: [
    ".review-content",
    ".comment-text",
    ".J-comment",
  ] as const,
  RATING: [
    ".star",
    ".score",
    '[class*="rating"]',
  ] as const,
  REPLY_TEXTAREA: [
    'textarea[class*="reply"]',
    'textarea[placeholder*="回复"]',
    ".reply-textarea",
  ] as const,
  PUBLISH_BUTTON: [
    ".submit-btn",
    ".send-btn",
    '[class*="submit"]',
  ] as const,
} as const;
