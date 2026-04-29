/* Ganje Research Tracking – app.js */

'use strict';

// ── Dark/light theme toggle ──────────────────────────────────
const THEME_KEY  = 'ganje-theme';
const html       = document.documentElement;
const themeBtn   = document.getElementById('theme-toggle');
const themeIcon  = document.getElementById('theme-icon');
const hlLight    = document.getElementById('hljs-light-theme');
const hlDark     = document.getElementById('hljs-dark-theme');

function applyTheme(theme) {
  html.setAttribute('data-bs-theme', theme);
  localStorage.setItem(THEME_KEY, theme);
  if (themeIcon) {
    themeIcon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
  }
  if (hlLight && hlDark) {
    hlLight.disabled = (theme === 'dark');
    hlDark.disabled  = (theme !== 'dark');
  }
}

// Apply saved or system preference on load
(function () {
  const saved  = localStorage.getItem(THEME_KEY);
  const system = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  applyTheme(saved || system);
})();

if (themeBtn) {
  themeBtn.addEventListener('click', () => {
    const current = html.getAttribute('data-bs-theme');
    applyTheme(current === 'dark' ? 'light' : 'dark');
  });
}

// ── Highlight.js – run on page load ─────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  if (typeof hljs !== 'undefined') {
    document.querySelectorAll('.markdown-body pre code').forEach(el => {
      hljs.highlightElement(el);
    });
  }
});

// ── Auto-submit the filter bar when status changes ───────────
// Scoped to the filter form (#filter-form) so it won't trigger on the
// artifact edit form's own status field.
document.addEventListener('DOMContentLoaded', () => {
  const statusSel = document.querySelector('#filter-form #id_status');
  if (statusSel) {
    statusSel.addEventListener('change', () => statusSel.form.submit());
  }
});
