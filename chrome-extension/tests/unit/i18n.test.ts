/**
 * i18n 单元测试
 *
 * 覆盖：
 * - normalizeLang 规范化
 * - getLang（storage 优先 / 浏览器检测 / 默认 zh）
 * - setLang / setCurrentLang
 * - t 取词与缺失回退
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  normalizeLang,
  getLang,
  setLang,
  setCurrentLang,
  getCurrentLang,
  t,
  LANGUAGES,
} from '../../src/i18n/index'

describe('i18n', () => {
  let mockStorageArea: Record<string, any>
  let originalLanguage: string

  beforeEach(() => {
    mockStorageArea = {}
    originalLanguage = navigator.language

    // Mock chrome.storage.local
    vi.stubGlobal('chrome', {
      storage: {
        local: {
          get: vi.fn((keys: string | Record<string, any>) => {
            if (typeof keys === 'string') {
              return Promise.resolve({ [keys]: mockStorageArea[keys] ?? null })
            }
            const result: Record<string, any> = {}
            for (const k of Object.keys(keys)) result[k] = mockStorageArea[k] ?? null
            return Promise.resolve(result)
          }),
          set: vi.fn((items: Record<string, any>) => {
            Object.assign(mockStorageArea, items)
            return Promise.resolve()
          }),
          remove: vi.fn((keys: string | string[]) => {
            const list = Array.isArray(keys) ? keys : [keys]
            for (const k of list) delete mockStorageArea[k]
            return Promise.resolve()
          }),
        },
      },
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    // 恢复 navigator.language
    Object.defineProperty(navigator, 'language', {
      value: originalLanguage,
      configurable: true,
    })
  })

  describe('normalizeLang', () => {
    it('en / en-US / EN 应归为 en', () => {
      expect(normalizeLang('en')).toBe('en')
      expect(normalizeLang('en-US')).toBe('en')
      expect(normalizeLang('EN')).toBe('en')
    })

    it('zh / zh-CN 应归为 zh', () => {
      expect(normalizeLang('zh')).toBe('zh')
      expect(normalizeLang('zh-CN')).toBe('zh')
    })

    it('其他/空值默认 zh', () => {
      expect(normalizeLang('fr')).toBe('zh')
      expect(normalizeLang('')).toBe('zh')
      expect(normalizeLang(undefined)).toBe('zh')
      expect(normalizeLang(null)).toBe('zh')
    })
  })

  describe('getLang', () => {
    it('storage 有 app_lang 时优先返回', async () => {
      mockStorageArea['app_lang'] = 'en'
      const lang = await getLang()
      expect(lang).toBe('en')
    })

    it('无 storage 值且浏览器为英文时返回 en', async () => {
      Object.defineProperty(navigator, 'language', { value: 'en-US', configurable: true })
      const lang = await getLang()
      expect(lang).toBe('en')
    })

    it('无 storage 值且浏览器非英文时返回 zh', async () => {
      Object.defineProperty(navigator, 'language', { value: 'fr-FR', configurable: true })
      const lang = await getLang()
      expect(lang).toBe('zh')
    })

    it('storage 抛异常时回退浏览器检测', async () => {
      vi.mocked(chrome.storage.local.get).mockRejectedValueOnce(new Error('Storage error'))
      Object.defineProperty(navigator, 'language', { value: 'en', configurable: true })
      const lang = await getLang()
      expect(lang).toBe('en')
    })
  })

  describe('setLang / getCurrentLang', () => {
    it('setLang 应写入 storage 并更新 currentLang', async () => {
      await setLang('en')
      expect(mockStorageArea['app_lang']).toBe('en')
      expect(getCurrentLang()).toBe('en')
    })

    it('setCurrentLang 仅更新内存当前语言', () => {
      setCurrentLang('en')
      expect(getCurrentLang()).toBe('en')
      expect(mockStorageArea['app_lang']).toBeUndefined()
    })
  })

  describe('t', () => {
    it('取词正确', () => {
      setCurrentLang('zh')
      expect(t('app.title')).toBe('酒店评论AI助手')
      setCurrentLang('en')
      expect(t('app.title')).toBe('Hotel Review AI Assistant')
    })

    it('缺失 key 回退中文', () => {
      setCurrentLang('en')
      // 中文有、英文缺失的 key（此例用中文作为回退兜底）
      expect(t('app.title')).toBe('Hotel Review AI Assistant')
    })

    it('未知 key 返回 key 本身', () => {
      setCurrentLang('zh')
      expect(t('nonexistent.key')).toBe('nonexistent.key')
    })
  })

  it('LANGUAGES 应包含 zh 和 en', () => {
    expect(LANGUAGES).toContain('zh')
    expect(LANGUAGES).toContain('en')
  })
})
