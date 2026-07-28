/**
 * OTA Adapter
 *
 * 抽象 OTA 页面 DOM 适配层。
 * 不同 OTA 平台（携程、飞猪、Booking 等）继承此类并实现各自的选择器和交互逻辑。
 *
 * 使用方式：
 *   const adapter = OTAAdapter.detect()
 *   if (adapter) {
 *     const review = adapter.getReviewContent()
 *     adapter.fillReply(text)
 *   }
 */

/**
 * OTA Adapter 基类
 */
export class OTAAdapter {
  /**
   * 检测当前页面是否匹配此 Adapter 的 OTA 平台。
   * 返回 true/false。
   */
  static matches() {
    return false;
  }

  /**
   * 获取页面评论内容。
   * 优先级：用户选中文本 > OTA 特定选择器 > 通用选择器
   */
  getReviewContent() {
    // Step 1: 用户选中的文本
    const sel = window.getSelection();
    if (sel && sel.toString().trim()) {
      return sel.toString().trim();
    }

    // Step 2: 通用选择器（所有 Adapter 共享）
    const genericSelectors = [
      '.review-content',
      '.review_text',
      '.comment-content',
      '#reviews .item',
      '[data-testid*="review"]',
      '.J-comment',
    ];

    for (const s of genericSelectors) {
      const el = document.querySelector(s);
      if (el && el.innerText?.trim()) {
        // 避免匹配到过宽的元素（超过 500 字的不像单条评论）
        const text = el.innerText.trim();
        if (text.length < 500) return text;
      }
    }

    return '';
  }

  /**
   * 将 AI 回复填充到 OTA 页面的回复框。
   * 使用 dispatchEvent 尝试触发前端框架（React/Vue）的状态更新。
   *
   * @param {string} text - AI 回复内容
   * @returns {boolean} 是否成功找到回复框并填充
   */
  fillReply(text) {
    const input = this._findReplyInput();
    if (!input) return false;

    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLTextAreaElement.prototype,
      'value'
    )?.set;

    if (nativeInputValueSetter) {
      nativeInputValueSetter.call(input, text);
    } else {
      input.value = text;
    }

    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));

    // React: 触发 React 内部 input tracker
    input.dispatchEvent(new Event('input', { bubbles: true }));

    return true;
  }

  /**
   * 尝试触发 OTA 页面的发布/提交操作。
   *
   * @returns {boolean} 是否成功找到并触发提交按钮
   */
  publish() {
    const button = this._findPublishButton();
    if (!button) return false;
    button.click();
    return true;
  }

  /**
   * 查找回复输入框（子类可覆盖以使用特定选择器）
   */
  _findReplyInput() {
    const selectors = [
      '.reply-input',
      '.reply-textarea',
      'textarea[class*="reply"]',
      'textarea[class*="response"]',
      'textarea[placeholder*="回复"]',
      'textarea[placeholder*="评价"]',
    ];

    for (const s of selectors) {
      const el = document.querySelector(s);
      if (el) return el;
    }

    // Fallback: 页面上第一个可见的 textarea
    for (const ta of document.querySelectorAll('textarea')) {
      if (ta.offsetParent !== null) return ta;
    }

    return null;
  }

  /**
   * 查找提交按钮（子类可覆盖）
   */
  _findPublishButton() {
    const selectors = [
      '.submit-btn',
      '.send-btn',
      'button[type="submit"]',
      '[class*="submit"]',
      '[class*="send"]',
      '[class*="publish"]',
      'button:contains("提交")',
      'button:contains("发布")',
      'button:contains("发送")',
    ];

    for (const s of selectors) {
      const btn = document.querySelector(s);
      if (btn) return btn;
    }

    return null;
  }

  /**
   * 自动检测当前页面匹配的 Adapter。
   * 返回 OTAAdapter 实例或 null。
   */
  static detect() {
    const adapters = [].concat(
      // 后续添加：CtripAdapter, MeituanAdapter, FliggyAdapter 等
    );

    for (const AdapterClass of adapters) {
      if (AdapterClass.matches()) {
        return new AdapterClass();
      }
    }

    // 无特定匹配时返回基类实例（使用通用选择器）
    return new OTAAdapter();
  }
}
