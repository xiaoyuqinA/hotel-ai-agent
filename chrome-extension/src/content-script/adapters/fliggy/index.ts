import type { OTAAdapter } from "../types.js";
import type { ReviewContext } from "../../../state/review.js";
import { SELECTORS } from "./selectors.js";

export class FliggyAdapter implements OTAAdapter {
  readonly name = "fliggy";

  async matches(): Promise<boolean> {
    try {
      const result = await chrome.storage.local.get("__HOTEL_AI_TEST_MODE");
      if (result["__HOTEL_AI_TEST_MODE"]) return true;
    } catch {}
    return location.hostname.includes("fliggy.com");
  }

  async getReview(): Promise<ReviewContext | null> {
    const sel = window.getSelection();
    if (sel?.toString().trim()) {
      return { platform: "fliggy", content: sel.toString().trim() };
    }
    for (const s of SELECTORS.REVIEW_CONTENT) {
      const el = document.querySelector(s);
      const text = (el as HTMLElement)?.innerText?.trim();
      if (text && text.length < 500) {
        return {
          platform: "fliggy",
          content: text,
          rating: this._extractRating(el),
        };
      }
    }
    return null;
  }

  async fillReply(reply: string): Promise<boolean> {
    const textarea = this._findTextarea();
    if (!textarea) return false;
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set;
    if (setter) setter.call(textarea, reply);
    else textarea.value = reply;
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    textarea.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }

  async publish(): Promise<boolean> {
    throw new Error("manual confirm required");
  }

  private _findTextarea(): HTMLTextAreaElement | null {
    for (const s of SELECTORS.REPLY_TEXTAREA) {
      const el = document.querySelector(s);
      if (el) return el as HTMLTextAreaElement;
    }
    for (const ta of document.querySelectorAll("textarea")) {
      if (ta.offsetParent !== null) return ta;
    }
    return null;
  }

  private _extractRating(el: Element | null): number | undefined {
    if (!el) return undefined;
    for (const s of SELECTORS.RATING) {
      const ratingEl = el.closest("[class*='review']")?.querySelector(s);
      if (ratingEl?.textContent) {
        const num = parseFloat(ratingEl.textContent);
        if (!isNaN(num)) return num;
      }
    }
    return undefined;
  }
}
