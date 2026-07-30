/**
 * GenericAdapter — 通用页面适配
 *
 * 当无 OTA 平台匹配时兜底使用。
 * 评论获取：仅通过用户选中文本。
 * 回复填充：查找页面第一个可见 textarea 并填入。
 *
 * publish: 不做自动发布，throw manual confirm
 */

import type { OTAAdapter } from '../types.js';
import type { ReviewContext } from '../../../state/review.js';

export class GenericAdapter implements OTAAdapter {
  readonly name = 'generic';
  private _lastSelection = '';

  initialize(): void {
    document.addEventListener('selectionchange', () => {
      this._lastSelection = window.getSelection()?.toString().trim() ?? '';
    });
  }

  async matches(): Promise<boolean> {
    return true; // 始终兜底匹配
  }

  async getReview(): Promise<ReviewContext | null> {
    // 仅通过用户选中的文本获取评论
    if (this._lastSelection) {
      return { platform: 'generic', content: this._lastSelection };
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
    throw new Error('manual confirm required');
  }

  private _findTextarea(): HTMLTextAreaElement | null {
    for (const ta of document.querySelectorAll('textarea')) {
      if (ta.offsetParent !== null) return ta;
    }
    return null;
  }
}
