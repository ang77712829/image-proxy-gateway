const STORAGE_KEY = 'studio_theme';
const THEMES = ['dark', 'light'];

let currentTheme = 'dark';

function normalizeTheme(value) {
  return THEMES.includes(value) ? value : 'dark';
}

export function applyTheme(theme) {
  currentTheme = normalizeTheme(theme);
  document.documentElement.dataset.theme = currentTheme;
  return currentTheme;
}

export function initTheme() {
  let stored = '';
  try {
    stored = localStorage.getItem(STORAGE_KEY) || '';
  } catch (_) {
    stored = '';
  }
  return applyTheme(stored || document.documentElement.dataset.theme || 'dark');
}

export function getTheme() {
  return currentTheme;
}

export function toggleTheme() {
  const next = currentTheme === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  try {
    localStorage.setItem(STORAGE_KEY, next);
  } catch (_) {
    /* non-sensitive UI preference write failed */
  }
  return next;
}
