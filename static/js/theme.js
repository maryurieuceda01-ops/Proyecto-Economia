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

// Notificación para el botón ENVIAR (blog.html)
document.addEventListener('DOMContentLoaded', function() {
  const subscribeBtn = document.getElementById('subscribeBtn');
  const subscribeToast = document.getElementById('subscribeToast');
  const subEmail = document.getElementById('sub-email');
  if (subscribeBtn && subscribeToast && subEmail) {
    subscribeBtn.addEventListener('click', function() {
      // Validación simple de email
      const email = subEmail.value;
      if (!email || !email.includes('@')) {
        subscribeToast.textContent = 'Por favor ingresa un correo válido.';
        subscribeToast.classList.add('visible');
        setTimeout(() => {
          subscribeToast.classList.remove('visible');
          subscribeToast.textContent = 'Gracias, te tendremos al día con las noticias!';
        }, 1800);
        return;
      }
      subscribeToast.textContent = '¡Gracias! Te has suscrito exitosamente.';
      subscribeToast.classList.add('visible');
      setTimeout(() => {
        subscribeToast.classList.remove('visible');
        subscribeToast.textContent = 'Gracias, te tendremos al día con las noticias!';
      }, 2200);
      subEmail.value = '';
    });
  }
});