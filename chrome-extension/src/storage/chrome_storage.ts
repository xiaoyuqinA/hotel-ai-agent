/**
 * ChromeStorage — Chrome Storage API 封装
 *
 * 职责：
 * 1. 封装 chrome.storage.local 的 get/set/remove
 * 2. 提供类型安全的泛型接口
 * 3. 统一错误处理
 *
 * 未来 chrome.storage.sync 可替换为 SessionStorage 实现同一接口
 */

export class ChromeStorage {
  /**
   * 获取存储项
   */
  async get<T>(key: string): Promise<T | null> {
    try {
      const result = await chrome.storage.local.get(key);
      return (result[key] as T) ?? null;
    } catch (error) {
      console.error(`[ChromeStorage] Failed to get "${key}":`, error);
      return null;
    }
  }

  /**
   * 设置存储项
   */
  async set(key: string, value: unknown): Promise<void> {
    try {
      await chrome.storage.local.set({ [key]: value });
    } catch (error) {
      console.error(`[ChromeStorage] Failed to set "${key}":`, error);
      throw error;
    }
  }

  /**
   * 删除存储项
   */
  async remove(key: string): Promise<void> {
    try {
      await chrome.storage.local.remove(key);
    } catch (error) {
      console.error(`[ChromeStorage] Failed to remove "${key}":`, error);
      throw error;
    }
  }

  /**
   * 清空所有存储项（慎用）
   */
  async clear(): Promise<void> {
    try {
      await chrome.storage.local.clear();
    } catch (error) {
      console.error('[ChromeStorage] Failed to clear:', error);
      throw error;
    }
  }
}

/** 单例 */
export const chromeStorage = new ChromeStorage();
