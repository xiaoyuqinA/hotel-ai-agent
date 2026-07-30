/**
 * HotelConfigService 单元测试
 *
 * 覆盖：
 * - createHotel（生成 ID、时戳、默认设置）
 * - getHotel / listHotels
 * - updateReplySettings / updateCurrentReplySettings
 * - getCurrentReplySettings（各级 fallback）
 * - currentHotel 管理（set/get/clear/删除时自动清除）
 * - deleteHotel 级联清除 current_hotel
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { HotelConfigService } from '../../src/config/service'
import { LocalHotelConfigRepository } from '../../src/config/local_repository'
import type { HotelConfig, ReplySettings } from '../../src/config/models'
import { DEFAULT_REPLY_SETTINGS } from '../../src/config/models'

describe('HotelConfigService', () => {
  let service: HotelConfigService
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

    service = new HotelConfigService(new LocalHotelConfigRepository())
  })

  // ── createHotel ──────────────────────────────────────────────────────────

  describe('createHotel', () => {
    it('应生成 ID 和时间戳', async () => {
      const hotel = await service.createHotel({ name: '测试酒店', city: '深圳' })

      expect(hotel.id).toMatch(/^hotel_\d+$/)
      expect(hotel.name).toBe('测试酒店')
      expect(hotel.city).toBe('深圳')
      expect(hotel.created_at).toBeGreaterThan(0)
      expect(hotel.updated_at).toBe(hotel.created_at)
    })

    it('应填充默认 reply_settings', async () => {
      const hotel = await service.createHotel({ name: '测试', city: '深圳' })

      expect(hotel.reply_settings.tone).toBe(DEFAULT_REPLY_SETTINGS.tone)
      expect(hotel.reply_settings.style).toBe(DEFAULT_REPLY_SETTINGS.style)
      expect(hotel.reply_settings.rules).toEqual(DEFAULT_REPLY_SETTINGS.rules)
    })

    it('应接受部分 reply_settings 覆盖', async () => {
      const hotel = await service.createHotel({
        name: '测试',
        city: '深圳',
        reply_settings: { tone: '温暖', style: '简短', rules: ['规则1'] },
      })

      expect(hotel.reply_settings.tone).toBe('温暖')
      expect(hotel.reply_settings.style).toBe('简短')
      expect(hotel.reply_settings.rules).toEqual(['规则1'])
    })

    it('应持久化到 storage', async () => {
      const hotel = await service.createHotel({ name: '持久化测试', city: '广州' })
      const saved = mockStorageArea['hotel_configs'] as HotelConfig[]
      expect(saved).toHaveLength(1)
      expect(saved[0].id).toBe(hotel.id)
    })
  })

  // ── getHotel / listHotels ───────────────────────────────────────────────

  describe('getHotel / listHotels', () => {
    it('listHotels 应返回按 name 查找的酒店', async () => {
      await service.createHotel({ name: '酒店A', city: '深圳' })
      const hotels = await service.listHotels()
      expect(hotels.length).toBeGreaterThanOrEqual(1)
      expect(hotels.some(h => h.name === '酒店A')).toBe(true)
    })

    it('getHotel 应返回指定酒店', async () => {
      await service.createHotel({ name: '酒店A', city: '深圳' })
      const hotels = await service.listHotels()
      const target = hotels.find(h => h.name === '酒店A')
      expect(target).toBeDefined()

      const result = await service.getHotel(target!.id)
      expect(result).not.toBeNull()
      expect(result!.name).toBe('酒店A')
    })

    it('getHotel 不存在的 ID 返回 null', async () => {
      const result = await service.getHotel('nonexistent')
      expect(result).toBeNull()
    })
  })

  // ── updateReplySettings ─────────────────────────────────────────────────

  describe('updateReplySettings', () => {
    it('应更新指定酒店的回复设置', async () => {
      const hotel = await service.createHotel({ name: '测试', city: '深圳' })

      const newSettings: ReplySettings = { tone: '温暖', style: '轻松', rules: ['规则1'] }
      await service.updateReplySettings(hotel.id, newSettings)

      const updated = await service.getHotel(hotel.id)
      expect(updated!.reply_settings).toEqual(newSettings)
      expect(updated!.updated_at).toBeGreaterThanOrEqual(hotel.created_at)
    })

    it('酒店不存在应抛出错误', async () => {
      await expect(
        service.updateReplySettings('nonexistent', DEFAULT_REPLY_SETTINGS)
      ).rejects.toThrow('Hotel not found: nonexistent')
    })
  })

  // ── deleteHotel ─────────────────────────────────────────────────────────

  describe('deleteHotel', () => {
    it('应删除指定酒店', async () => {
      const hotel = await service.createHotel({ name: '待删除', city: '深圳' })
      await service.deleteHotel(hotel.id)

      const result = await service.getHotel(hotel.id)
      expect(result).toBeNull()
    })

    it('删除当前选中酒店时应自动清除 current_hotel', async () => {
      const hotel = await service.createHotel({ name: '当前酒店', city: '深圳' })
      await service.setCurrentHotel({ hotel_id: hotel.id, hotel_name: hotel.name })

      await service.deleteHotel(hotel.id)

      const current = await service.getCurrentHotel()
      expect(current).toBeNull()
    })

    it('删除非当前酒店不应影响 current_hotel', async () => {
      // 预置数据避免 Date.now() 同时 ID 冲突
      const hotelA = await service.createHotel({ name: 'A', city: '深圳' })
      const hotelB = await service.createHotel({ name: 'B', city: '北京' })
      // 若 ID 冲突（同一毫秒），手动修改 hotelB 的 ID
      if (hotelA.id === hotelB.id) {
        hotelB.id = 'hotel_distinct_' + Date.now() + Math.random()
        await service['repository'].save(hotelB)
      }

      await service.setCurrentHotel({ hotel_id: hotelA.id, hotel_name: hotelA.name })

      await service.deleteHotel(hotelB.id)

      const current = await service.getCurrentHotel()
      expect(current).not.toBeNull()
      expect(current!.hotel_id).toBe(hotelA.id)
    })
  })

  // ── currentHotel 管理 ───────────────────────────────────────────────────

  describe('currentHotel 管理', () => {
    it('初始应为 null', async () => {
      const current = await service.getCurrentHotel()
      expect(current).toBeNull()
    })

    it('setCurrentHotel 应持久化', async () => {
      await service.setCurrentHotel({ hotel_id: 'hotel_1', hotel_name: '测试酒店' })
      const current = await service.getCurrentHotel()
      expect(current).toEqual({ hotel_id: 'hotel_1', hotel_name: '测试酒店' })
    })

    it('clearCurrentHotel 应清除', async () => {
      await service.setCurrentHotel({ hotel_id: 'hotel_1', hotel_name: '测试酒店' })
      await service.clearCurrentHotel()
      const current = await service.getCurrentHotel()
      expect(current).toBeNull()
    })
  })

  // ── getCurrentReplySettings ─────────────────────────────────────────────

  describe('getCurrentReplySettings', () => {
    it('未设当前酒店应返回默认设置', async () => {
      const settings = await service.getCurrentReplySettings()
      expect(settings).toEqual(DEFAULT_REPLY_SETTINGS)
    })

    it('当前酒店存在应返回其设置', async () => {
      const hotel = await service.createHotel({ name: '测试', city: '深圳' })
      await service.setCurrentHotel({ hotel_id: hotel.id, hotel_name: hotel.name })

      const settings = await service.getCurrentReplySettings()
      expect(settings.tone).toBe(DEFAULT_REPLY_SETTINGS.tone)
    })

    it('当前酒店有自定义设置应返回自定义值', async () => {
      const hotel = await service.createHotel({
        name: '测试',
        city: '深圳',
        reply_settings: { tone: '自定义语气', style: '自定义风格', rules: ['规则'] },
      })
      await service.setCurrentHotel({ hotel_id: hotel.id, hotel_name: hotel.name })

      const settings = await service.getCurrentReplySettings()
      expect(settings.tone).toBe('自定义语气')
      expect(settings.style).toBe('自定义风格')
    })
  })

  // ── updateCurrentReplySettings ──────────────────────────────────────────

  describe('updateCurrentReplySettings', () => {
    it('应更新当前酒店的回复设置', async () => {
      const hotel = await service.createHotel({ name: '测试', city: '深圳' })
      await service.setCurrentHotel({ hotel_id: hotel.id, hotel_name: hotel.name })

      await service.updateCurrentReplySettings({
        tone: '新语气',
        style: '新风格',
        rules: ['新规则'],
      })

      const updated = await service.getHotel(hotel.id)
      expect(updated!.reply_settings.tone).toBe('新语气')
    })

    it('未设当前酒店应抛出错误', async () => {
      await expect(
        service.updateCurrentReplySettings(DEFAULT_REPLY_SETTINGS)
      ).rejects.toThrow('No current hotel selected')
    })
  })
})
