// ===== Configuración de la versión publicada =====
// Se rellena al desplegar con la URL del backend (Render) y del .exe (GitHub Releases).

// URL del backend FastAPI (sin barra final). Vacío = mismo origen (servidor local).
const API_BASE = 'https://turboxclipspro-api.onrender.com';

// URL pública del instalador Windows (GitHub Releases).
const DOWNLOAD_URL = 'https://github.com/lordtrvr/turboxclipspro/releases/download/v1.0/TurboxClipsPro.exe';

// Número de WhatsApp (con código de país, sin +)
const ADMIN_WHATSAPP = '18293670355';

function apiUrl(path) {
  if (!path) return path;
  if (/^https?:\/\//i.test(path)) return path;
  if (path.indexOf('data:') === 0) return path;
  return (API_BASE || '') + path;
}
