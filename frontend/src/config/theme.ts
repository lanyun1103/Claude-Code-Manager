const STORAGE_KEY = 'cc_theme';

export type Theme = 'dark' | 'light';

export function getTheme(): Theme {
  return (localStorage.getItem(STORAGE_KEY) as Theme) || 'dark';
}

export function setTheme(theme: Theme) {
  localStorage.setItem(STORAGE_KEY, theme);
  applyTheme(theme);
}

export function toggleTheme(): Theme {
  const next = getTheme() === 'dark' ? 'light' : 'dark';
  setTheme(next);
  return next;
}

export function applyTheme(theme?: Theme) {
  const t = theme || getTheme();
  document.documentElement.classList.toggle('light', t === 'light');
}
