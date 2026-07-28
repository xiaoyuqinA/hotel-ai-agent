/**
 * Adapter Registry — OTA 平台检测注册
 *
 * 新增 OTA 平台时：
 * 1. 实现 OTAAdapter 接口
 * 2. 在 adapters 数组中添加实例
 *
 * Content script 零改动。
 */

import type { OTAAdapter } from './types.js';
import { CtripAdapter } from './ctrip/index.js';

const adapters: OTAAdapter[] = [
  new CtripAdapter(),
  // 后续: new BookingAdapter(), new FliggyAdapter(), ...
];

/**
 * 检测当前页面匹配的 OTA Adapter
 * @returns 匹配的 adapter 实例，无匹配返回 null
 */
export function detectAdapter(): OTAAdapter | null {
  for (const adapter of adapters) {
    if (adapter.matches()) return adapter;
  }
  return null;
}
