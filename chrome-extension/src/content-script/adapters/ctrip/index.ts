/**
 * CtripAdapter — 携程 OTA 页面适配
 *
 * 支持域名：hotels.ctrip.com, YOU.ctrip.com, ctrip.com
 * 选择器定义见 ./selectors.ts
 */

import type { OTAAdapter } from '../types.js';
import type { ReviewContext } from '../../../state/review.js';
import { SELECTORS } from './selectors.js';

export class CtripAdapter implements OTAAdapter {
  readonly name = 'ctrip';

  matches(): boolean {
    return location.hostname.includes('ctrip.com');
  }

  async getReview(): Promise<ReviewContext | null> {
    // Step 1: 用户选中文本优先
    const sel = window.getSelection();
    if (sel?.toString().trim()) {
      return { platform: 'ctrip', content: sel.toString().trim() };
    }

    // Step 2: 携程特定选择器
    for (const s of SELECTORS.REVIEW_CONTENT) {
      const el = document.querySelector(s);
      const text = el?.innerText?.trim();
      if (text && text.length < 500) {
        return {
          platform: 'ctrip',
          content: text,
          reviewId: el?.closest('[data-review-id]')?.getAttribute('data-review-id') ?? undefined,
          rating: this._extractRating(el),
        };
      }
    }

    return null;
  }

  async fillReply(reply: string): Promise<boolean> {
    const textarea = this._findTextarea();
    if (!textarea) return false;

    const setter = Object.getOwnPropertyDescriptor(
      HTMLTextAreaElement.prototype, 'value'
    )?.set;

    if (setter) {
      setter.call(textarea, reply);
    } else {
      textarea.value = reply;
    }

    textarea.dispatchEvent(new Event('input', { bubbles: true }));
    textarea.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  }

  async publish(): Promise<boolean> {
    // MVP 阶段：保留接口，不自动发布
    throw new Error('manual confirm required');
  }

  private _findTextarea(): HTMLTextAreaElement | null {
    for (const s of SELECTORS.REPLY_TEXTAREA) {
      const el = document.querySelector(s);
      if (el) return el as HTMLTextAreaElement;
    }
    // fallback: 第一个可见 textarea
    for (const ta of document.querySelectorAll('textarea')) {
      if (ta.offsetParent !== null) return ta;
    }
    return null;
  }

  private _extractRating(el: Element): number | undefined {
    const reviewCard = el.closest('[class*="review"]');
    if (!reviewCard) return undefined;
    for (const s of SELECTORS.RATING) {
      const ratingEl = reviewCard.querySelector(s);
      if (ratingEl?.textContent) {
        const num = parseFloat(ratingEl.textContent);
        if (!isNaN(num)) return num;
      }
    }
    return undefined;
  }
}
