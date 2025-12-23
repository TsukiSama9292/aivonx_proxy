(function () {
  const STORAGE_KEY = 'ui-theme';
  const THEME_TOGGLE_ID = 'themeToggle';
  const THEME_ICON_ID = 'themeIcon';
  const DARK_MQL = '(prefers-color-scheme: dark)';

  function safeGet(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }

  function safeSet(key, val) {
    try { localStorage.setItem(key, val); } catch (e) { /* ignore */ }
  }

  function systemPrefersDark() {
    return !!(window.matchMedia && window.matchMedia(DARK_MQL).matches);
  }

  function updateButtonState(theme) {
    const btn = document.getElementById(THEME_TOGGLE_ID);
    const icon = document.getElementById(THEME_ICON_ID);

    const isDark = theme === 'dark';

    if (btn) {
      btn.classList.toggle('active', isDark);
      btn.setAttribute('aria-pressed', String(isDark));
      btn.title = isDark ? 'Switch to light mode' : 'Switch to dark mode';
    }

    if (icon) {
      icon.textContent = isDark ? '🌙' : '☀️';
    }
  }

  function applyTheme(theme) {
    const isDark = theme === 'dark';
    if (isDark) {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    updateButtonState(theme);
  }

  function resolveInitialTheme() {
    const stored = safeGet(STORAGE_KEY);
    if (stored === 'dark' || stored === 'light') return stored;
    return systemPrefersDark() ? 'dark' : 'light';
  }

  function getCurrentTheme() {
    return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
  }

  function toggleTheme() {
    const next = getCurrentTheme() === 'dark' ? 'light' : 'dark';
    safeSet(STORAGE_KEY, next);
    applyTheme(next);
  }

  // init ASAP (avoid flash)
  try {
    applyTheme(resolveInitialTheme());
  } catch (e) { /* ignore */ }

  document.addEventListener('DOMContentLoaded', function () {
    const btn = document.getElementById(THEME_TOGGLE_ID);
    if (!btn) return;

    btn.addEventListener('click', toggleTheme);
    updateButtonState(getCurrentTheme());
  });

  // follow system changes only when user has not set an explicit preference
  if (window.matchMedia) {
    const mql = window.matchMedia(DARK_MQL);

    const handleChange = (e) => {
      if (!safeGet(STORAGE_KEY)) {
        applyTheme(e.matches ? 'dark' : 'light');
      }
    };

    mql.addEventListener('change', handleChange);
  }
})();
