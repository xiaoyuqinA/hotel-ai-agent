/**
 * InviteCodeService 单元测试
 *
 * 覆盖：
 * - get / set / remove 存储
 * - validate 验证逻辑（mock fetch）
 * - checkCurrent 无码/有码
 * - 空值/空字符串边界
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { InviteCodeService } from '../../src/config/invite_service'

describe('InviteCodeService', () => {
  let service: InviteCodeService
  let mockStorageArea: Record<string, any>

  beforeEach(() => {
    mockStorageArea = {}

    vi.stubGlobal('chrome', {
      runtime: {
        sendMessage: vi.fn().mockResolvedValue({ apiUrl: 'http://localhost:8000' }),
        id: 'test-extension-id',
      },
      storage: {
        local: {
          get: vi.fn((key: string) => {
            return Promise.resolve({ [key]: mockStorageArea[key] ?? null })
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
        },
      },
    })

    service = new InviteCodeService()
  })

  // ── get / set / remove ──────────────────────────────────────────────────────

  describe('get / set / remove', () => {
    it('初始应返回 null', async () => {
      const result = await service.get()
      expect(result).toBeNull()
    })

    it('set 后 get 应返回保存的值', async () => {
      await service.set('INVITE-ABC123')
      const result = await service.get()
      expect(result).toBe('INVITE-ABC123')
    })

    it('set 应覆盖已有值', async () => {
      await service.set('INVITE-OLD')
      await service.set('INVITE-NEW')
      const result = await service.get()
      expect(result).toBe('INVITE-NEW')
    })

    it('remove 后应返回 null', async () => {
      await service.set('INVITE-TO-REMOVE')
      await service.remove()
      const result = await service.get()
      expect(result).toBeNull()
    })

    it('空字符串不应等于 null', async () => {
      await service.set('')
      const result = await service.get()
      expect(result).toBe('')
    })

    it('多次 remove 不应报错', async () => {
      await service.remove()
      await service.remove()
      const result = await service.get()
      expect(result).toBeNull()
    })
  })

  // ── validate ────────────────────────────────────────────────────────────────

  describe('validate', () => {
    it('有效邀请码应返回 valid=true', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ valid: true }),
      }))

      const result = await service.validate('INVITE-VALID')
      expect(result.valid).toBe(true)
    })

    it('不存在的邀请码 404 应返回 valid=false', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
      }))

      const result = await service.validate('INVITE-NOT-FOUND')
      expect(result.valid).toBe(false)
      expect(result.message).toBe('邀请码不存在')
    })

    it('过期的邀请码 410 应返回 valid=false', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
        ok: false,
        status: 410,
      }))

      const result = await service.validate('INVITE-EXPIRED')
      expect(result.valid).toBe(false)
      expect(result.message).toBe('邀请码已过期')
    })

    it('其他错误状态码应返回 valid=false', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
      }))

      const result = await service.validate('INVITE-ERROR')
      expect(result.valid).toBe(false)
      expect(result.message).toBe('验证失败')
    })

    it('网络错误应返回 valid=false', async () => {
      vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network error')))

      const result = await service.validate('INVITE-NET')
      expect(result.valid).toBe(false)
      expect(result.message).toBe('无法连接服务器')
    })

    it('该 API 地址应来自 chrome.runtime.sendMessage', async () => {
      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ valid: true }),
      })
      vi.stubGlobal('fetch', fetchMock)

      await service.validate('INVITE-TEST')

      const calledUrl = fetchMock.mock.calls[0][0]
      expect(calledUrl).toContain('localhost:8000/api/invite/validate')

      // 验证 POST body 中包含邀请码
      const calledBody = fetchMock.mock.calls[0][1].body
      const parsed = JSON.parse(calledBody)
      expect(parsed.code).toBe('INVITE-TEST')
    })
  })

  // ── checkCurrent ───────────────────────────────────────────────────────────

  describe('checkCurrent', () => {
    it('未设置邀请码应返回 valid=false', async () => {
      const result = await service.checkCurrent()
      expect(result.valid).toBe(false)
      expect(result.message).toBe('未设置邀请码')
    })

    it('有邀请码时调 validate', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ valid: true }),
      }))

      await service.set('INVITE-CHECK')
      const result = await service.checkCurrent()
      expect(result.valid).toBe(true)
    })
  })
})
