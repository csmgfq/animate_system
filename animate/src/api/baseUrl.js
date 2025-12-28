// Centralized API base url helper for Vue CLI builds.
// - Priority: localStorage custom config > VUE_APP_API_BASE > auto-detect
// - In normal http(s) dev: return '' so calls become '/api/...' and can be proxied.
// - In Electron/file/other protocols: fall back to http://localhost:8088 (or VUE_APP_API_FALLBACK).

const STORAGE_KEY = 'customApiServer';

export function getCustomServerConfig() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (e) {
    // ignore
  }
  return null;
}

export function setCustomServerConfig(ip, port, protocol = 'http') {
  try {
    if (ip && port) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ ip, port, protocol }));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  } catch (e) {
    // ignore
  }
}

export function getApiBaseUrl() {
  // 1. Check localStorage for custom server config
  const custom = getCustomServerConfig();
  if (custom && custom.ip && custom.port) {
    const protocol = custom.protocol || 'http';
    return `${protocol}://${custom.ip}:${custom.port}`;
  }

  // 2. Check environment variable
  const raw = (process.env.VUE_APP_API_BASE || '').trim();
  if (raw) return raw.replace(/\/+$/, '');

  // 3. Browser runtime fallback
  try {
    if (typeof window !== 'undefined' && window.location && window.location.protocol) {
      const protocol = window.location.protocol;
      if (protocol === 'http:' || protocol === 'https:') {
        return '';
      }
    }
  } catch (e) {
    // ignore
  }

  const fallback = (process.env.VUE_APP_API_FALLBACK || 'http://localhost:8088').trim();
  return fallback.replace(/\/+$/, '');
}
