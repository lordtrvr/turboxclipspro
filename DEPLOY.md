# TurboxClipsPro â€” GuÃ­a de publicaciÃ³n 24/7 (sin PC)

## Arquitectura

| Parte | Servicio gratuito | QuÃ© hace |
|-------|------------------|----------|
| PÃ¡gina web | **Netlify** | HTML/CSS/JS (landing, registro, login, dashboard) |
| Backend + API | **Render** | FastAPI: registro, verificaciÃ³n, login, admin |
| Base de datos | **Neon** | PostgreSQL gratis (persistente) |
| Instalador `.exe` | **GitHub Releases** | Archivo de 107 MB, descarga pÃºblica |

> Render gratis se duerme tras ~15 min sin uso y "despierta" en ~30 s al recibir una visita.
> Si quieres que despierte al instante, puedes aÃ±adir un monitor gratuito (UptimeRobot, cada 5 min).

---

## Paso 1 â€” GitHub ( cuenta + repositorio )

1. Ir a https://github.com/signup y crear cuenta con tu email.
2. Verificar el email.
3. Crear repositorio **pÃºblico** llamado `turboxclipspro`.
4. No marcar "Initialize with README".

---

## Paso 2 â€” Neon ( base de datos )

1. Ir a https://neon.tech y registrarse con GitHub (botÃ³n "Continue with GitHub").
2. Crear un proyecto: nombre `turboxclipspro`, regiÃ³n la mÃ¡s cercana.
3. Copiar la **connection string** ( parece `postgresql://neondb_owner:...@ep-xxx.region.aws.neon.tech/neondb?sslmode=require` ).
4. Guardarla, se usarÃ¡ como `DATABASE_URL`.

---

## Paso 3 â€” Subir el cÃ³digo y el .exe

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

## Paso 4 â€” Migrar los usuarios actuales

```powershell
$env:DATABASE_URL = "postgresql://...copiado de Neon..."
python backend/migrate_to_postgres.py
```

---

## Paso 5 â€” Render ( backend )

1. Ir a https://render.com y registrarse con GitHub.
2. **New â†’ Web Service** â†’ conectar el repo `turboxclipspro`.
3. ConfiguraciÃ³n:
   - Runtime: `Python 3`
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - Plan: Free
4. En **Environment Variables** aÃ±adir:

| Variable | Valor |
|----------|-------|
| `SECRET_KEY` | clave larga aleatoria |
| `DATABASE_URL` | cadena de Neon |
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | `turboxclips@gmail.com` |
| `SMTP_PASS` | contraseÃ±a de aplicaciÃ³n de Gmail |
| `SMTP_FROM` | `TurboxClipsPro <turboxclips@gmail.com>` |
| `APP_NAME` | `TurboxClipsPro` |
| `APP_URL` | URL de Render (se completa tras el deploy) |
| `DOWNLOAD_URL` | URL del `.exe` en GitHub Releases |
| `ADMIN_WHATSAPP` | `18293670355` |
| `ADMIN_PASSWORD` | contraseÃ±a del panel |
| `ADMIN_ACCESS_KEY` | clave del enlace directo |
| `FRONTEND_URL` | URL de Netlify (se completa tras el deploy) |

5. Crear el servicio. Copiar la URL pÃºblica (`https://turboxclipspro-api.onrender.com`).

---

## Paso 6 â€” Netlify ( frontend )

OpciÃ³n A â€” desde GitHub:
1. Ir a https://netlify.com y registrarse con GitHub.
2. **Add new site â†’ Import an existing project** â†’ elegir el repo.
3. Build settings:
   - Base directory: (vacÃ­o)
   - Build command: (vacÃ­o)
   - Publish directory: `frontend`
4. Deploy.

OpciÃ³n B â€” Netlify CLI:
```powershell
npm i -g netlify-cli
netlify login
netlify init
netlify deploy --prod
```

---

## Paso 7 â€” Conectar frontend con backend

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
Actualizar tambiÃ©n `FRONTEND_URL` y `APP_URL` en Render con las URLs reales.

---

## RevocaciÃ³n remota del `.exe`

El ejecutable consulta una lista pÃºblica de IDs de licencias revocadas al abrirse y luego cada 5 minutos:

```
https://raw.githubusercontent.com/lordtrvr/turboxclipspro-revoked/main/revoked.json
```

Para revocar una licencia:

1. En la app de administrador, abrir **Administrador** y marcar la key como revocada (esto escribe `owner/revoked.json`).
2. Copiar ese contenido a `revoked.json` en https://github.com/lordtrvr/turboxclipspro-revoked (editar el archivo desde GitHub).
3. La key deja de funcionar al reabrir la app, o en un mÃ¡ximo de 5 minutos si estaba abierta.

> El repo de revocaciÃ³n es pÃºblico y gratuito. No hace falta republish el `.exe` para revocar: solo se actualiza ese JSON.

---

## Paso 8 â€” Probar

- https://TU-SITIO.netlify.app â†’ landing
- Registro con email real â†’ llega el cÃ³digo
- Verificar â†’ dashboard
- BotÃ³n descargar â†’ baja el `.exe`
- `https://TU-API.onrender.com/admin?key=CLAVE` â†’ panel de administraciÃ³n
