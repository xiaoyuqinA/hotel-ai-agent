/**
 * ChromeStorage 单元测试
 *
 * 覆盖：
 * - get/set/remove/clear 基础操作
 * - 不存在的 key 返回 null
 * - 错误处理（storage 抛异常时的兜底行为）
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ChromeStorage } from '../../src/storage/chrome_storage'

describe('ChromeStorage', () => {
  let storage: ChromeStorage
  let mockStorageArea: Record<string, any>

  beforeEach(() => {
    mockStorageArea = {}

    // Mock chrome.storage.local
    vi.stubGlobal('chrome', {
      storage: {
        local: {
          get: vi.fn((keys: string | string[] | Record<string, any>) => {
            if (typeof keys === 'string') {
              return Promise.resolve({ [keys]: mockStorageArea[keys] ?? null })
            }
            // 数组/对象形式返回匹配的内容
            const result: Record<string, any> = {}
            const keyList = Array.isArray(keys) ? keys : Object.keys(keys)
            for (const k of keyList) {
              result[k] = mockStorageArea[k] ?? null
            }
            return Promise.resolve(result)
          }),
          set: vi.fn((items: Record<string, any>) => {
            Object.assign(mockStorageArea, items)
            return Promise.resolve()
          }),
          remove: vi.fn((keys: string | string[]) => {
            const keyList = Array.isArray(keys) ? keys : [keys]
            for (const k of keyList) {
              delete mockStorageArea[k]
            }
            return Promise.resolve()
          }),
          clear: vi.fn(() => {
            mockStorageArea = {}
            return Promise.resolve()
          }),
        },
      },
    })

    storage = new ChromeStorage()
  })

  describe('get', () => {
    it('存在 key 应返回对应的值', async () => {
      mockStorageArea['name'] = 'test-hotel'
      const result = await storage.get<string>('name')
      expect(result).toBe('test-hotel')
    })

    it('不存在的 key 应返回 null', async () => {
      const result = await storage.get<string>('nonexistent')
      expect(result).toBeNull()
    })

    it('null 值应返回 null', async () => {
      mockStorageArea['empty'] = null
      const result = await storage.get('empty')
      expect(result).toBeNull()
    })

    it('复杂对象应正确反序列化', async () => {
      const obj = { id: '1', name: 'test', nested: { value: 42 } }
      mockStorageArea['config'] = obj
      const result = await storage.get<typeof obj>('config')
      expect(result).toEqual(obj)
    })

    it('storage 抛异常应返回 null 不崩溃', async () => {
      vi.mocked(chrome.storage.local.get).mockRejectedValueOnce(new Error('Storage error'))
      const result = await storage.get('key')
      expect(result).toBeNull()
    })

    it('数组值应正确返回', async () => {
      const arr = [{ id: '1' }, { id: '2' }]
      mockStorageArea['items'] = arr
      const result = await storage.get<typeof arr>('items')
      expect(result).toHaveLength(2)
      expect(result![0].id).toBe('1')
    })
  })

  describe('set', () => {
    it('应存储字符串值', async () => {
      await storage.set('key', 'value')
      expect(mockStorageArea['key']).toBe('value')
      expect(chrome.storage.local.set).toHaveBeenCalledWith({ key: 'value' })
    })

    it('应存储对象值', async () => {
      const obj = { a: 1, b: 2 }
      await storage.set('config', obj)
      expect(mockStorageArea['config']).toEqual(obj)
    })

    it('应覆盖已有值', async () => {
      mockStorageArea['key'] = 'old'
      await storage.set('key', 'new')
      expect(mockStorageArea['key']).toBe('new')
    })

    it('storage 抛异常应抛出', async () => {
      vi.mocked(chrome.storage.local.set).mockRejectedValueOnce(new Error('Quota exceeded'))
      await expect(storage.set('key', 'value')).rejects.toThrow('Quota exceeded')
    })
  })

  describe('remove', () => {
    it('应删除存在的 key', async () => {
      mockStorageArea['key'] = 'value'
      await storage.remove('key')
      expect(mockStorageArea['key']).toBeUndefined()
    })

    it('删除不存在的 key 不应报错', async () => {
      await expect(storage.remove('nonexistent')).resolves.toBeUndefined()
    })

    it('storage 抛异常应抛出', async () => {
      vi.mocked(chrome.storage.local.remove).mockRejectedValueOnce(new Error('Remove error'))
      await expect(storage.remove('key')).rejects.toThrow('Remove error')
    })
  })

  describe('clear', () => {
    it('应清空所有数据', async () => {
      mockStorageArea['a'] = 1
      mockStorageArea['b'] = 2
      await storage.clear()
      expect(Object.keys(mockStorageArea)).toHaveLength(0)
    })

    it('空 storage 清空不应报错', async () => {
      await expect(storage.clear()).resolves.toBeUndefined()
    })

    it('storage 抛异常应抛出', async () => {
      vi.mocked(chrome.storage.local.clear).mockRejectedValueOnce(new Error('Clear error'))
      await expect(storage.clear()).rejects.toThrow('Clear error')
    })
  })
})
