/**
 * LocalHotelConfigRepository 单元测试
 *
 * 覆盖：
 * - list / findById / save / delete / updateReplySettings
 * - 空列表/不存在时的兜底行为
 * - 更新 vs 创建（save 的 upsert 语义）
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { LocalHotelConfigRepository } from '../../src/config/local_repository'
import type { HotelConfig, ReplySettings } from '../../src/config/models'
import { DEFAULT_REPLY_SETTINGS } from '../../src/config/models'

describe('LocalHotelConfigRepository', () => {
  let repo: LocalHotelConfigRepository
  let mockStorageArea: Record<string, any>

  beforeEach(() => {
    mockStorageArea = {}

    vi.stubGlobal('chrome', {
      storage: {
        local: {
          get: vi.fn((key: string) => {
            return Promise.resolve({ [key]: mockStorageArea[key] ?? null })
          }),
          set: vi.fn((items: Record<string, any>) => {
            Object.assign(mockStorageArea, items)
            return Promise.resolve()
          }),
          remove: vi.fn(() => Promise.resolve()),
        },
      },
    })

    repo = new LocalHotelConfigRepository()
  })

  function makeHotel(overrides: Partial<HotelConfig> = {}): HotelConfig {
    return {
      id: 'hotel_1',
      name: '测试酒店',
      city: '深圳',
      reply_settings: { ...DEFAULT_REPLY_SETTINGS },
      created_at: 1000,
      updated_at: 1000,
      ...overrides,
    }
  }

  describe('list', () => {
    it('空存储应返回空数组', async () => {
      const hotels = await repo.list()
      expect(hotels).toEqual([])
    })

    it('应返回所有酒店', async () => {
      const hotels = [makeHotel({ id: '1' }), makeHotel({ id: '2' })]
      mockStorageArea['hotel_configs'] = hotels

      const result = await repo.list()
      expect(result).toHaveLength(2)
      expect(result[0].id).toBe('1')
      expect(result[1].id).toBe('2')
    })

    it('null 存储应返回空数组', async () => {
      mockStorageArea['hotel_configs'] = null
      const result = await repo.list()
      expect(result).toEqual([])
    })
  })

  describe('findById', () => {
    it('存在应返回酒店', async () => {
      mockStorageArea['hotel_configs'] = [
        makeHotel({ id: 'hotel_1', name: '酒店A' }),
        makeHotel({ id: 'hotel_2', name: '酒店B' }),
      ]

      const result = await repo.findById('hotel_2')
      expect(result).not.toBeNull()
      expect(result!.name).toBe('酒店B')
    })

    it('不存在应返回 null', async () => {
      mockStorageArea['hotel_configs'] = [makeHotel({ id: 'hotel_1' })]
      const result = await repo.findById('nonexistent')
      expect(result).toBeNull()
    })

    it('空列表应返回 null', async () => {
      const result = await repo.findById('any')
      expect(result).toBeNull()
    })
  })

  describe('save', () => {
    it('应创建新酒店', async () => {
      const hotel = makeHotel({ id: 'new_hotel' })
      await repo.save(hotel)

      const hotels = mockStorageArea['hotel_configs'] as HotelConfig[]
      expect(hotels).toHaveLength(1)
      expect(hotels[0].id).toBe('new_hotel')
    })

    it('存在时应更新覆盖', async () => {
      mockStorageArea['hotel_configs'] = [makeHotel({ id: 'hotel_1', name: '旧名称' })]

      await repo.save(makeHotel({ id: 'hotel_1', name: '新名称' }))

      const hotels = mockStorageArea['hotel_configs'] as HotelConfig[]
      expect(hotels).toHaveLength(1)
      expect(hotels[0].name).toBe('新名称')
    })

    it('应追加而非覆盖其他酒店', async () => {
      mockStorageArea['hotel_configs'] = [makeHotel({ id: 'hotel_1' })]

      await repo.save(makeHotel({ id: 'hotel_2' }))

      const hotels = mockStorageArea['hotel_configs'] as HotelConfig[]
      expect(hotels).toHaveLength(2)
    })

    it('空列表时应正确创建第一条', async () => {
      await repo.save(makeHotel({ id: 'first' }))

      const hotels = mockStorageArea['hotel_configs'] as HotelConfig[]
      expect(hotels).toHaveLength(1)
      expect(hotels[0].id).toBe('first')
    })
  })

  describe('delete', () => {
    it('应删除指定酒店', async () => {
      mockStorageArea['hotel_configs'] = [
        makeHotel({ id: 'a' }),
        makeHotel({ id: 'b' }),
        makeHotel({ id: 'c' }),
      ]

      await repo.delete('b')

      const hotels = mockStorageArea['hotel_configs'] as HotelConfig[]
      expect(hotels).toHaveLength(2)
      expect(hotels.map(h => h.id)).toEqual(['a', 'c'])
    })

    it('删除不存在的不报错', async () => {
      mockStorageArea['hotel_configs'] = [makeHotel({ id: 'a' })]
      await expect(repo.delete('nonexistent')).resolves.toBeUndefined()
      expect(mockStorageArea['hotel_configs']).toHaveLength(1)
    })

    it('空列表删除不报错', async () => {
      await expect(repo.delete('any')).resolves.toBeUndefined()
    })
  })

  describe('updateReplySettings', () => {
    it('应更新指定酒店的回复设置', async () => {
      mockStorageArea['hotel_configs'] = [
        makeHotel({ id: 'hotel_1', reply_settings: { ...DEFAULT_REPLY_SETTINGS, tone: '旧语气' } }),
      ]

      const newSettings: ReplySettings = { tone: '专业', style: '正式', rules: ['规则1'] }
      await repo.updateReplySettings('hotel_1', newSettings)

      const hotels = mockStorageArea['hotel_configs'] as HotelConfig[]
      expect(hotels[0].reply_settings).toEqual(newSettings)
      expect(hotels[0].updated_at).toBeGreaterThan(1000)
    })

    it('酒店不存在应抛出错误', async () => {
      await expect(
        repo.updateReplySettings('nonexistent', DEFAULT_REPLY_SETTINGS)
      ).rejects.toThrow('Hotel not found: nonexistent')
    })
  })
})
