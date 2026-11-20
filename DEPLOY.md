# TurboxClipsPro — Guía de publicación 24/7 (sin PC)

## Arquitectura

| Parte | Servicio gratuito | Qué hace |
|-------|------------------|----------|
| Página web | **Netlify** | HTML/CSS/JS (landing, registro, login, dashboard) |
| Backend + API | **Render** | FastAPI: registro, verificación, login, admin |
| Base de datos | **Neon** | PostgreSQL gratis (persistente) |
| Instalador `.exe` | **GitHub Releases** | Archivo de 107 MB, descarga pública |

> Render gratis se duerme tras ~15 min sin uso y "despierta" en ~30 s al recibir una visita.
> Si quieres que despierte al instante, puedes añadir un monitor gratuito (UptimeRobot, cada 5 min).

---

## Paso 1 — GitHub ( cuenta + repositorio )

1. Ir a https://github.com/signup y crear cuenta con tu email.
2. Verificar el email.
3. Crear repositorio **público** llamado `turboxclipspro`.
4. No marcar "Initialize with README".

---

## Paso 2 — Neon ( base de datos )

1. Ir a https://neon.tech y registrarse con GitHub (botón "Continue with GitHub").
2. Crear un proyecto: nombre `turboxclipspro`, región la más cercana.
3. Copiar la **connection string** ( parece `postgresql://neondb_owner:...@ep-xxx.region.aws.neon.tech/neondb?sslmode=require` ).
4. Guardarla, se usará como `DATABASE_URL`.

---

## Paso 3 — Subir el código y el .exe

Desde la carpeta del proyecto:

```powershell
cd C:\Users\potii\Desktop\TurboxWeb
git init
git remote add origin https://github.com/TU-USUARIO/turboxclipspro.git
git add .
git commit -m "TurboxClipsPro deploy"
git branch -M main
git push -u origin main
```

El `.exe` **no** va en el repo (107 MB). Se sube a una Releases:

```powershell
gh release create v1.0 downloads/TurboxClipsPro.exe --title "TurboxClipsPro 1.0" --generate-notes
```

La URL de descarga ya publicada es:
```
https://github.com/lordtrvr/turboxclipspro/releases/download/v1.0/TurboxClipsPro.exe
```
SHA256 verificado: `BD777647A2621E52F413230EEC410920D179FC9957CBA2BC3D35681EF9274A1B`

---

## Paso 4 — Migrar los usuarios actuales

```powershell
$env:DATABASE_URL = "postgresql://...copiado de Neon..."
python backend/migrate_to_postgres.py
```

---

## Paso 5 — Render ( backend )

1. Ir a https://render.com y registrarse con GitHub.
2. **New → Web Service** → conectar el repo `turboxclipspro`.
3. Configuración:
   - Runtime: `Python 3`
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - Plan: Free
4. En **Environment Variables** añadir:

| Variable | Valor |
|----------|-------|
| `SECRET_KEY` | clave larga aleatoria |
| `DATABASE_URL` | cadena de Neon |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | `turboxclips@gmail.com` |
| `SMTP_PASS` | contraseña de aplicación de Gmail |
| `SMTP_FROM` | `TurboxClipsPro <turboxclips@gmail.com>` |
| `APP_NAME` | `TurboxClipsPro` |
| `APP_URL` | URL de Render (se completa tras el deploy) |
| `DOWNLOAD_URL` | URL del `.exe` en GitHub Releases |
| `ADMIN_WHATSAPP` | `18293670355` |
| `ADMIN_PASSWORD` | contraseña del panel |
| `ADMIN_ACCESS_KEY` | clave del enlace directo |
| `FRONTEND_URL` | URL de Netlify (se completa tras el deploy) |

5. Crear el servicio. Copiar la URL pública (`https://turboxclipspro-api.onrender.com`).

---

## Paso 6 — Netlify ( frontend )

Opción A — desde GitHub:
1. Ir a https://netlify.com y registrarse con GitHub.
2. **Add new site → Import an existing project** → elegir el repo.
3. Build settings:
   - Base directory: (vacío)
   - Build command: (vacío)
   - Publish directory: `frontend`
4. Deploy.

Opción B — Netlify CLI:
```powershell
npm i -g netlify-cli
netlify login
netlify init
netlify deploy --prod
```

---

## Paso 7 — Conectar frontend con backend

Editar `frontend/js/config.js`:

```js
const API_BASE = 'https://turboxclipspro-api.onrender.com';
const DOWNLOAD_URL = 'https://github.com/lordtrvr/turboxclipspro/releases/download/v1.0/TurboxClipsPro.exe';
```

URLs reales:
- Frontend: https://turboxclipspro.netlify.app
- Backend: https://turboxclipspro-api.onrender.com
- Admin: https://turboxclipspro-api.onrender.com/admin?key=YuhrXmPsfM9kPqg3BKxYhjWf2S8NFfrlEoIuDKsm

Hacer commit y push. Netlify y Render se actualizan solos.
Actualizar también `FRONTEND_URL` y `APP_URL` en Render con las URLs reales.

---

## Revocación remota del `.exe`

El ejecutable consulta una lista pública de IDs de licencias revocadas al abrirse y luego cada 5 minutos:

```
https://raw.githubusercontent.com/lordtrvr/turboxclipspro-revoked/main/revoked.json
```

Para revocar una licencia:

1. En la app de administrador, abrir **Administrador** y marcar la key como revocada (esto escribe `owner/revoked.json`).
2. Copiar ese contenido a `revoked.json` en https://github.com/lordtrvr/turboxclipspro-revoked (editar el archivo desde GitHub).
3. La key deja de funcionar al reabrir la app, o en un máximo de 5 minutos si estaba abierta.

> El repo de revocación es público y gratuito. No hace falta republish el `.exe` para revocar: solo se actualiza ese JSON.

---

## Paso 8 — Probar

- https://TU-SITIO.netlify.app → landing
- Registro con email real → llega el código
- Verificar → dashboard
- Botón descargar → baja el `.exe`
- `https://TU-API.onrender.com/admin?key=CLAVE` → panel de administración
