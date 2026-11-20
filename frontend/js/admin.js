// ===== Panel de administración =====
(function () {
  const loginView = document.getElementById('adminLogin');
  const panelView = document.getElementById('adminPanel');
  if (!loginView || !panelView) return;
  window.__adminReady = true;

  // El panel no debe depender de app.js: definimos helpers si no estan disponibles
  if (typeof window.api !== 'function') {
    window.api = async function (path, options) {
      const res = await fetch(apiUrl(path), Object.assign({ credentials: 'include' }, options || {}));
      let data = null;
      try { data = await res.json(); } catch (e) { data = null; }
      if (!res.ok) throw new Error((data && (data.detail || data.message)) || res.statusText || 'Error');
      return data;
    };
  }
  if (typeof window.showToast !== 'function') {
    window.showToast = function (message, isError) {
      window.alert((isError ? 'Error: ' : '') + message);
    };
  }

  const form = document.getElementById('adminLoginForm');
  const passwordInput = document.getElementById('adminPassword');
  const errorBox = document.getElementById('adminError');
  const loginBtn = document.getElementById('adminLoginBtn');
  const tbody = document.getElementById('usersBody');
  const searchInput = document.getElementById('adminSearch');
  const countLabel = document.getElementById('adminCount');
  const emptyLabel = document.getElementById('adminEmpty');

  let currentUsers = [];

  function showLogin() {
    panelView.hidden = true;
    loginView.hidden = false;
    if (passwordInput) passwordInput.value = '';
    setError('');
  }

  function showPanel() {
    loginView.hidden = true;
    panelView.hidden = false;
    setError('');
    loadUsers();
  }

  function setError(msg, info) {
    if (!errorBox) return;
    errorBox.textContent = msg || '';
    errorBox.classList.toggle('show', !!msg);
    errorBox.classList.toggle('info', !!info);
  }

  function fmtDate(value) {
    if (!value) return '—';
    return value.replace('T', ' ').slice(0, 16);
  }

  function makeCell(text, className) {
    const td = document.createElement('td');
    td.textContent = text == null || text === '' ? '—' : text;
    if (className) td.className = className;
    return td;
  }

  function renderRows(users) {
    tbody.innerHTML = '';
    const term = (searchInput.value || '').trim().toLowerCase();
    const shown = users.filter((u) => {
      if (!term) return true;
      const full = ((u.first_name || '') + ' ' + (u.last_name || '') + ' ' + (u.email || '')).toLowerCase();
      return full.indexOf(term) !== -1;
    });

    shown.forEach((u) => {
      const tr = document.createElement('tr');
      tr.dataset.id = u.id;

      // Usuario + avatar
      const userCell = document.createElement('td');
      const userWrap = document.createElement('div');
      userWrap.className = 'admin-user-cell';
      const img = document.createElement('img');
      img.className = 'admin-avatar';
      img.alt = '';
      img.src = apiUrl(u.avatar || ('/api/avatar/default/' + u.id));
      img.onerror = function () { this.src = apiUrl('/api/avatar/default/' + u.id); this.onerror = null; };
      const nameWrap = document.createElement('div');
      const strong = document.createElement('strong');
      strong.textContent = ((u.first_name || '') + ' ' + (u.last_name || '')).trim() || 'Sin nombre';
      const small = document.createElement('small');
      small.textContent = '#' + u.id;
      nameWrap.appendChild(strong);
      nameWrap.appendChild(small);
      userWrap.appendChild(img);
      userWrap.appendChild(nameWrap);
      userCell.appendChild(userWrap);
      tr.appendChild(userCell);

      tr.appendChild(makeCell(u.email));
      tr.appendChild(makeCell(u.country));
      tr.appendChild(makeCell(fmtDate(u.created_at), 'admin-date'));

      const statusCell = document.createElement('td');
      const badge = document.createElement('span');
      badge.className = 'admin-badge ' + (u.is_verified ? 'ok' : 'pending');
      badge.textContent = u.is_verified ? 'Verificado' : 'Pendiente';
      statusCell.appendChild(badge);
      tr.appendChild(statusCell);

      const actions = document.createElement('td');
      const actionsWrap = document.createElement('div');
      actionsWrap.className = 'admin-actions';

      const verifyBtn = document.createElement('button');
      verifyBtn.className = 'btn btn-ghost btn-sm';
      verifyBtn.textContent = u.is_verified ? 'Desverificar' : 'Verificar';
      verifyBtn.addEventListener('click', () => toggleVerify(u.id));

      const delBtn = document.createElement('button');
      delBtn.className = 'btn btn-danger btn-sm';
      delBtn.textContent = 'Eliminar';
      delBtn.addEventListener('click', () => deleteUser(u.id, strong.textContent));

      actionsWrap.appendChild(verifyBtn);
      actionsWrap.appendChild(delBtn);
      actions.appendChild(actionsWrap);
      tr.appendChild(actions);

      tbody.appendChild(tr);
    });

    countLabel.textContent = shown.length + (shown.length === 1 ? ' usuario' : ' usuarios');
    emptyLabel.hidden = shown.length !== 0;
  }

  async function loadUsers() {
    try {
      const data = await api('/api/admin/users');
      currentUsers = data.users || [];
      const verified = currentUsers.filter((u) => u.is_verified).length;
      document.getElementById('statTotal').textContent = currentUsers.length;
      document.getElementById('statVerified').textContent = verified;
      document.getElementById('statPending').textContent = currentUsers.length - verified;
      renderRows(currentUsers);
    } catch (e) {
      if (e.message === 'No autorizado') return showLogin();
      showToast(e.message || 'No se pudieron cargar los registros', true);
    }
  }

  async function toggleVerify(id) {
    try {
      await api('/api/admin/users/' + id + '/verify', { method: 'POST' });
      showToast('Estado actualizado');
      loadUsers();
    } catch (e) {
      showToast(e.message || 'No se pudo actualizar', true);
    }
  }

  async function deleteUser(id, name) {
    if (!window.confirm('¿Eliminar permanentemente la cuenta de "' + name + '"?\nEsta acción no se puede deshacer.')) return;
    try {
      await api('/api/admin/users/' + id, { method: 'DELETE' });
      showToast('Usuario eliminado');
      loadUsers();
    } catch (e) {
      showToast(e.message || 'No se pudo eliminar', true);
    }
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    setError('Entrando...', true);
    loginBtn.disabled = true;
    loginBtn.textContent = 'Entrando...';
    try {
      const res = await fetch(apiUrl('/api/admin/login'), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: passwordInput.value })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'No se pudo entrar');
      showPanel();
    } catch (err) {
      setError(err.message || 'No se pudo entrar');
    } finally {
      loginBtn.disabled = false;
      loginBtn.textContent = 'Entrar al panel';
    }
  });

  document.getElementById('adminLogoutBtn').addEventListener('click', async (e) => {
    e.preventDefault();
    try { await api('/api/admin/logout', { method: 'POST' }); } catch (e2) {}
    showLogin();
  });

  document.getElementById('adminRefreshBtn').addEventListener('click', loadUsers);
  searchInput.addEventListener('input', () => renderRows(currentUsers));

  // Comprobar si ya hay sesión de administrador activa
  api('/api/admin/session')
    .then((data) => data && data.ok ? showPanel() : showLogin())
    .catch(() => showLogin());
})();
