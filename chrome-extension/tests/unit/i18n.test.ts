/**
 * i18n 单元测试
 *
 * 覆盖：
 * - normalizeLang 规范化
 * - getLang（仅依据 navigator.language，无 storage）
 * - setCurrentLang / getCurrentLang
 * - t 取词与缺失回退
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  normalizeLang,
  getLang,
  setCurrentLang,
  getCurrentLang,
  t,
  LANGUAGES,
} from '../../src/i18n/index'

describe('i18n', () => {
  let originalLanguage: string

  beforeEach(() => {
    originalLanguage = navigator.language
  })

  afterEach(() => {
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
    it('浏览器语言为英文时返回 en', () => {
      Object.defineProperty(navigator, 'language', { value: 'en-US', configurable: true })
      expect(getLang()).toBe('en')
    })

    it('浏览器语言为中文时返回 zh', () => {
      Object.defineProperty(navigator, 'language', { value: 'zh-CN', configurable: true })
      expect(getLang()).toBe('zh')
    })

    it('浏览器语言非英文时返回 zh', () => {
      Object.defineProperty(navigator, 'language', { value: 'fr-FR', configurable: true })
      expect(getLang()).toBe('zh')
    })
  })

  describe('setCurrentLang / getCurrentLang', () => {
    it('setCurrentLang 应更新内存当前语言', () => {
      setCurrentLang('en')
      expect(getCurrentLang()).toBe('en')
      setCurrentLang('zh')
      expect(getCurrentLang()).toBe('zh')
    })
  })

  describe('t', () => {
    it('取词正确', () => {
      setCurrentLang('zh')
      expect(t('app.title')).toBe('酒店评论AI助手')
      setCurrentLang('en')
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
