// ── SECUREVISION — TEMA GLOBAL ──

(function () {
  const html = document.documentElement;

  // Aplicar tema guardado ANTES de que el body se pinte (evita flash)
  const saved = localStorage.getItem('sv-theme') || 'dark';
  html.setAttribute('data-theme', saved);

  // Una vez el DOM está listo, sincronizar el ícono del botón
  document.addEventListener('DOMContentLoaded', function () {
    const btn = document.getElementById('themeToggle');
    if (!btn) return;

    // Poner ícono correcto
    btn.textContent = html.getAttribute('data-theme') === 'dark' ? '🌙' : '☀️';

    btn.addEventListener('click', function () {
      const current = html.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      html.setAttribute('data-theme', next);
      btn.textContent = next === 'dark' ? '🌙' : '☀️';
      localStorage.setItem('sv-theme', next);
    });
  });
})();