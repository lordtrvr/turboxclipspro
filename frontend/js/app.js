// ===== Utilities =====
function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function showError(msg) {
  const el = document.getElementById('error');
  if (el) { el.textContent = msg; el.classList.add('show'); }
}
function hideError() {
  const el = document.getElementById('error');
  if (el) { el.classList.remove('show'); }
}
function showSuccess(msg) {
  const el = document.getElementById('success');
  if (el) { el.textContent = msg; el.classList.add('show'); }
}

// Token JWT guardado localmente: funciona aunque frontend y backend esten en dominios distintos.
const TOKEN_KEY = 'tbx_access_token';
function saveToken(token) { try { localStorage.setItem(TOKEN_KEY, token); } catch (e) {} }
function getToken() { try { return localStorage.getItem(TOKEN_KEY) || ''; } catch (e) { return ''; } }
function clearToken() { try { localStorage.removeItem(TOKEN_KEY); } catch (e) {} }

async function api(path, options) {
  const opts = Object.assign({ credentials: 'include' }, options || {});
  const token = getToken();
  if (token) {
    opts.headers = Object.assign({}, opts.headers || {}, { 'Authorization': 'Bearer ' + token });
  }
  const res = await fetch(apiUrl(path), opts);
  let data = null;
  try { data = await res.json(); } catch (e) { data = null; }
  if (!res.ok) {
    const msg = (data && (data.detail || data.message)) || res.statusText || 'Error';
    throw new Error(msg);
  }
  return data;
}

// ===== Page-specific logic =====
function initPage() {
  // Animate on scroll
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const delay = el.dataset.delay || 0;
        setTimeout(() => el.classList.add('animated'), +delay);
        observer.unobserve(el);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('[data-animate]').forEach((el) => observer.observe(el));

  // FAQ accordion
  document.querySelectorAll('.faq-q').forEach((btn) => {
    btn.addEventListener('click', () => {
      btn.parentElement.classList.toggle('open');
    });
  });

  // ===== Register =====
  const registerForm = document.getElementById('registerForm');
  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideError();
      const fd = new FormData(registerForm);
      const email = fd.get('email');
      const password = fd.get('password');
      const firstName = fd.get('first_name');
      const lastName = fd.get('last_name');
      const country = fd.get('country');
      const birthDate = fd.get('birth_date');

      try {
        const data = await api('/api/register', {
          method: 'POST',
          body: new URLSearchParams({
            email, password,
            first_name: firstName,
            last_name: lastName,
            country, birth_date: birthDate,
          }),
        });
        showSuccess(data.message || 'Registro exitoso. Revisa tu email para verificar tu cuenta.');
        setTimeout(() => {
          window.location.href = '/verify?email=' + encodeURIComponent(email);
        }, 2000);
      } catch (err) {
        showError(err.message || 'Error al registrar');
      }
    });
  }

  // ===== Login =====
  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideError();
      const fd = new FormData(loginForm);
      const email = fd.get('email');
      const password = fd.get('password');

      try {
        const data = await api('/api/login', {
          method: 'POST',
          body: new URLSearchParams({ email, password }),
        });
        if (data && data.token) saveToken(data.token);
        showSuccess('Inicio de sesión exitoso. Redirigiendo...');
        setTimeout(() => { window.location.href = '/dashboard'; }, 800);
      } catch (err) {
        showError(err.message || 'Email o contraseña incorrectos');
      }
    });
  }

  // ===== Verify =====
  const verifyForm = document.getElementById('verifyForm');
  if (verifyForm) {
    const params = new URLSearchParams(window.location.search);
    const emailParam = params.get('email');
    if (emailParam) {
      const emailInput = document.getElementById('email');
      if (emailInput) emailInput.value = emailParam;
    }

    verifyForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      hideError();
      const email = document.getElementById('email').value;
      const code = document.getElementById('code').value;
      try {
        const data = await api('/api/verify', {
          method: 'POST',
          body: new URLSearchParams({ email, code }),
        });
        if (data && data.token) saveToken(data.token);
        showSuccess(data.message || 'Email verificado exitosamente. Redirigiendo...');
        setTimeout(() => { window.location.href = '/dashboard'; }, 1500);
      } catch (err) {
        showError(err.message || 'Código incorrecto');
      }
    });

    const resendLink = document.getElementById('resendLink');
    if (resendLink) {
      resendLink.addEventListener('click', async (e) => {
        e.preventDefault();
        hideError();
        const email = document.getElementById('email').value;
        if (!email) { showError('Ingresa tu email primero'); return; }
        try {
          const data = await api('/api/resend-code', {
            method: 'POST',
            body: new URLSearchParams({ email }),
          });
          showSuccess(data.message || 'Código reenviado. Revisa tu bandeja.');
        } catch (err) {
          showError(err.message || 'Error al reenviar');
        }
      });
    }
  }

  // ===== Dashboard =====
  if (window.location.pathname === '/dashboard') {
    loadDashboard();
  }

  // ===== Logout (dashboard) =====
  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', async () => {
      try { await api('/api/logout', { method: 'POST' }); } catch (e) {}
      clearToken();
      window.location.href = '/';
    });
  }

  // ===== Nav auth state (home page) =====
  async function updateNavAuth() {
    const navActions = document.getElementById('navActions');
    if (!navActions) return;
    try {
      const user = await api('/api/me');
      document.querySelectorAll('[data-auth="guest"]').forEach(el => el.style.display = 'none');
      document.querySelectorAll('[data-auth="user"]').forEach(el => el.style.display = '');
      const nameEl = document.getElementById('navUserName');
      if (nameEl) nameEl.textContent = user.first_name || user.email;
    } catch (e) {
      document.querySelectorAll('[data-auth="user"]').forEach(el => el.style.display = 'none');
      document.querySelectorAll('[data-auth="guest"]').forEach(el => el.style.display = '');
    }
  }
  // Run now (if DOM ready) and also on load, to be safe
  updateNavAuth();
  window.addEventListener('load', updateNavAuth);
  const navLogout = document.getElementById('navLogoutBtn');
  if (navLogout) {
    navLogout.addEventListener('click', async () => {
      try { await api('/api/logout', { method: 'POST' }); } catch (e) {}
      clearToken();
      window.location.href = '/';
    });
  }
}

// Run init when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initPage);
} else {
  initPage();
}

function showToast(message, isError) {
  let box = document.getElementById('toastBox');
  if (!box) {
    box = document.createElement('div');
    box.id = 'toastBox';
    box.className = 'toast-box';
    document.body.appendChild(box);
  }
  const t = document.createElement('div');
  t.className = 'toast' + (isError ? ' toast-error' : '');
  t.textContent = message;
  box.appendChild(t);
  requestAnimationFrame(() => t.classList.add('is-visible'));
  setTimeout(() => {
    t.classList.remove('is-visible');
    setTimeout(() => t.remove(), 350);
  }, 3200);
}

async function loadDashboard() {
  try {
    const user = await api('/api/me');
    const un = document.getElementById('userName'); if (un) un.textContent = user.first_name || user.email;

    const full = document.getElementById('profileFullName');
    if (full) full.textContent = ((user.first_name || '') + ' ' + (user.last_name || '')).trim() || user.email;
    const sub = document.getElementById('profileEmailSub'); if (sub) sub.textContent = user.email || '—';

    const pf = document.getElementById('profileFirstName'); if (pf) pf.textContent = user.first_name || '—';
    const pl = document.getElementById('profileLastName'); if (pl) pl.textContent = user.last_name || '—';
    const pe = document.getElementById('profileEmail'); if (pe) pe.textContent = user.email || '—';
    const pc = document.getElementById('profileCountry'); if (pc) pc.textContent = user.country || '—';
    const pb = document.getElementById('profileBirth'); if (pb) pb.textContent = user.birth_date || '—';

    const ps = document.getElementById('profileStatus');
    if (ps) {
      ps.textContent = user.is_verified ? '✓ Verificado' : '⏳ Pendiente';
      ps.classList.toggle('is-verified', !!user.is_verified);
      ps.classList.toggle('is-pending', !user.is_verified);
    }

    const av = document.getElementById('profileAvatar');
    if (av) {
      av.style.opacity = '0';
      av.onload = () => { av.style.opacity = '1'; };
      av.src = apiUrl(user.avatar || ('/api/avatar/default/' + user.id));
    }

    const input = document.getElementById('avatarInput');
    if (input) input.addEventListener('change', async function () {
      const file = this.files && this.files[0];
      if (!file) return;
      const fd = new FormData();
      fd.append('file', file);
      try {
        const headers = {};
        const t = getToken();
        if (t) headers['Authorization'] = 'Bearer ' + t;
        const res = await fetch(apiUrl('/api/avatar'), { method: 'POST', body: fd, credentials: 'include', headers });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'No se pudo actualizar la foto');
        if (av) {
          av.style.opacity = '0';
          setTimeout(() => { av.src = apiUrl(data.avatar) + (data.avatar.indexOf('data:') === 0 ? '' : '?t=' + Date.now()); }, 180);
        }
        showToast('Foto de perfil actualizada');
      } catch (e) {
        showToast(e.message || 'No se pudo actualizar la foto', true);
      }
      this.value = '';
    });

    try {
      const dl = await api('/api/download');
      const btn = document.getElementById('downloadBtn');
      if (btn) { btn.href = apiUrl(dl.url); btn.setAttribute('download', dl.filename || 'TurboxClipsPro.exe'); }
    } catch (e) {}
  } catch (err) {
    window.location.href = '/login';
  }
}