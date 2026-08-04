/**
 * i18n 语言管理
 *
 * 职责：
 * 1. 读取/写入当前语言（chrome.storage.local['app_lang']）
 * 2. 未设置时自动检测浏览器语言（navigator.language）
 * 3. 提供 t(key) 翻译函数，缺失时回退中文
 *
 * 语言存储统一用 key `app_lang`，popup 与 content-script 共享。
 *
 * 用法：
 *   const lang = await getLang();
 *   setCurrentLang(lang);   // 初始化一次
 *   t('home.tone')          // 之后直接同步取词
 */

import zh from './zh.js';
import en from './en.js';

export type Lang = 'zh' | 'en';

export const LANGUAGES: Lang[] = ['zh', 'en'];

const STORAGE_KEY = 'app_lang';

const DICTIONARIES: Record<Lang, Record<string, string>> = {
  zh,
  en,
};

// 当前语言（由 setCurrentLang 设置，t() 依赖它）
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

/** 读取当前语言（storage → 浏览器检测 → 默认 zh） */
export async function getLang(): Promise<Lang> {
  try {
    const data = await chrome.storage.local.get(STORAGE_KEY);
    if (data && data[STORAGE_KEY]) {
      return normalizeLang(data[STORAGE_KEY]);
    }
  } catch {
    // storage 不可用时走浏览器检测
  }
  return normalizeLang(navigator.language);
}

/** 写入语言（手动切换） */
export async function setLang(lang: Lang): Promise<void> {
  await chrome.storage.local.set({ [STORAGE_KEY]: lang });
  setCurrentLang(lang);
}

/** 取词（依赖 setCurrentLang 已设置） */
export function t(key: string): string {
  return DICTIONARIES[_currentLang]?.[key] ?? DICTIONARIES.zh[key] ?? key;
}

/** 便捷：初始化语言并设置 currentLang */
export async function initI18n(): Promise<Lang> {
  const lang = await getLang();
  setCurrentLang(lang);
  return lang;
}
