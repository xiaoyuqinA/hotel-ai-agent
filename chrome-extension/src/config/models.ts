/**
 * 配置领域模型
 *
 * 与后端 shared/hotel_config/models.py 保持字段一致。
 * 前端 Local Repository 和后端 API Repository 共用此模型。
 */

/** 回复设置 */
export interface ReplySettings {
  /** 回复语气（如：专业、温暖、真诚） */
  tone: string;

  /** 回复风格（如：正式但具有人情味） */
  style: string;

  /** 回复规则列表（每一条是一个规则） */
  rules: string[];
}

/** 酒店配置 */
export interface HotelConfig {
  /** 酒店 ID */
  id: string;

  /** 酒店名称 */
  name: string;

  /** 所在城市 */
  city: string;

  /** 回复设置 */
  reply_settings: ReplySettings;

  /** 创建时间戳 (ms) */
  created_at: number;

  /** 更新时间戳 (ms) */
  updated_at: number;
}

/** 当前选中酒店（存储在 chrome.storage 的轻量结构） */
export interface CurrentHotel {
  /** 酒店 ID */
  hotel_id: string;

  /** 酒店名称 */
  hotel_name: string;
}

/** 创建酒店的输入参数 */
export interface CreateHotelInput {
  name: string;
  city: string;
  reply_settings?: Partial<ReplySettings>;
}

/** 默认回复设置（中文，兼容旧调用） */
export const DEFAULT_REPLY_SETTINGS: ReplySettings = {
  tone: '专业、真诚',
  style: '正式且具有人情味',
  rules: [
    '投诉必须先表达歉意',
    '称呼对方为"尊敬的客人"',
    '回复控制在 100-200 字',
  ],
};

/** 英文默认回复设置 */
const DEFAULT_REPLY_SETTINGS_EN: ReplySettings = {
  tone: 'Professional, sincere',
  style: 'Formal but personable',
  rules: [
    'Always apologize first for complaints',
    'Address the guest as "Dear Guest"',
    'Keep replies between 100-200 characters',
  ],
};

/** 按语言返回默认回复设置 */
export function getDefaultReplySettings(lang: string): ReplySettings {
  return lang === 'en' ? DEFAULT_REPLY_SETTINGS_EN : DEFAULT_REPLY_SETTINGS;
}
