/**
 * i18n 语言管理
 *
 * 职责：
 * 1. 根据浏览器语言（navigator.language）自动检测界面语言
 * 2. 提供 t(key) 翻译函数，缺失时回退中文
 *
 * 说明：语言完全跟随浏览器，不提供手动切换、不持久化。
 *
 * 用法：
 *   const lang = await initI18n();  // 初始化并设置 currentLang
 *   t('home.tone')                  // 之后直接同步取词
 */

import zh from './zh.js';
import en from './en.js';

export type Lang = 'zh' | 'en';

export const LANGUAGES: Lang[] = ['zh', 'en'];

const DICTIONARIES: Record<Lang, Record<string, string>> = {
  zh,
  en,
};

// 当前语言（由 initI18n/setCurrentLang 设置，t() 依赖它）
let _currentLang: Lang = 'zh';

/** 将任意语言标签规范化为支持的 Lang */
export function normalizeLang(value: string | undefined | null): Lang {
  if (!value) return 'zh';
  const lower = value.toLowerCase();
  if (lower.startsWith('en')) return 'en';
  return 'zh';
}

/** 设置当前语言（同步，供 t() 使用） */
export function setCurrentLang(lang: Lang): void {
  _currentLang = lang;
}

/** 获取当前语言（同步） */
export function getCurrentLang(): Lang {
  return _currentLang;
}

/** 检测浏览器语言（仅依据 navigator.language，不回退 storage） */
export function getLang(): Lang {
  return normalizeLang(navigator.language);
}

/** 取词（依赖 setCurrentLang 已设置） */
export function t(key: string): string {
  return DICTIONARIES[_currentLang]?.[key] ?? DICTIONARIES.zh[key] ?? key;
}

/** 便捷：初始化语言并设置 currentLang */
export async function initI18n(): Promise<Lang> {
  const lang = getLang();
  setCurrentLang(lang);
  return lang;
}
