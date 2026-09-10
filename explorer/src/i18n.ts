import en from "./locales/en-US.json";
import zh from "./locales/zh-CN.json";

export type Locale = "zh-CN" | "en-US";
export const LOCALE_STORAGE_KEY = "semantica.locale";

function readLocale(): Locale {
  if (typeof window !== "undefined") {
    const requested = new URLSearchParams(window.location.search).get("lang");
    if (requested === "zh-CN" || requested === "en-US") return requested;
  }
  try {
    return localStorage.getItem(LOCALE_STORAGE_KEY) === "en-US" ? "en-US" : "zh-CN";
  } catch {
    return "zh-CN";
  }
}

export const locale = readLocale();
export type MessageKey = keyof typeof en;
const reverseMessages = new Map(Object.entries(zh).map(([key, value]) => [value, key]));
const caseInsensitiveMessages = new Map(Object.keys(en).map(key => [key.toLowerCase(), key]));

/** Translate known interface values at the display boundary, preserving unknown data. */
export function displayText(value: string): string {
  const key = Object.prototype.hasOwnProperty.call(en, value) ? value : reverseMessages.get(value) ?? caseInsensitiveMessages.get(value.toLowerCase());
  return key ? t(key as MessageKey) : value;
}

/** Keep service diagnostics available separately from the localized interface message. */
export function errorText(value: unknown): string {
  const message = value instanceof Error ? value.message : typeof value === "string" ? value : "";
  const translated = displayText(message);
  if (translated !== message || Object.prototype.hasOwnProperty.call(en, message)) return translated;
  return t("Operation failed. Check the service connection and input.");
}
export let languageNavigationApproved = false;

export function t(key: MessageKey, values: Record<string, string | number> = {}): string {
  const messages = locale === "zh-CN" ? zh : en;
  return messages[key].replace(/\{(\w+)\}/g, (token, name: string) => (
    Object.prototype.hasOwnProperty.call(values, name) ? String(values[name]) : token
  ));
}

export function saveLocale(next: Locale): void {
  languageNavigationApproved = true;
  try {
    localStorage.setItem(LOCALE_STORAGE_KEY, next);
  } catch {
    // The language URL parameter still works when browser storage is disabled.
  }
}

if (typeof document !== "undefined") {
  document.documentElement.lang = locale;
  document.title = locale === "zh-CN" ? "K-Onto Graph 知识探索" : "K-Onto Graph Knowledge Explorer";
}
