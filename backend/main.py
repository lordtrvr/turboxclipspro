import base64
import csv
import hashlib
import io
import os
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .config import settings
from .models import Base, User
from .auth import (
    hash_password, verify_password, create_access_token, decode_token,
    generate_verification_code, code_expiry,
)
from .email_service import send_verification_email, send_welcome_email

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

# Sincroniza la secuencia de IDs en PostgreSQL tras migraciones con IDs explícitos.
if "postgresql" in settings.DATABASE_URL:
    with engine.begin() as _conn:
        _seq = _conn.exec_driver_sql("SELECT pg_get_serial_sequence('users', 'id')").scalar()
        if _seq:
            _max = _conn.exec_driver_sql("SELECT COALESCE(MAX(id), 1) FROM users").scalar()
            _last = _conn.exec_driver_sql(f"SELECT last_value FROM {_seq}").scalar()
            _target = max(int(_max or 1), int(_last or 1))
            _conn.exec_driver_sql(f"SELECT setval('{_seq}', {_target})")

# Migración ligera (solo SQLite; PostgreSQL ya crea la columna con create_all).
if "sqlite" in settings.DATABASE_URL:
    with engine.begin() as _conn:
        _cols = {r[1] for r in _conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()}
        if "avatar" not in _cols:
            _conn.exec_driver_sql("ALTER TABLE users ADD COLUMN avatar TEXT")

app = FastAPI(title=settings.APP_NAME)

_origins = [o.strip() for o in settings.FRONTEND_URL.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins + ["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)
AVATARS_DIR = FRONTEND_DIR / "avatars"
AVATARS_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
app.mount("/downloads", StaticFiles(directory=str(DOWNLOADS_DIR)), name="downloads")
templates = Jinja2Templates(directory=str(FRONTEND_DIR))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="No autenticado")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    user = db.query(User).filter(User.id == int(payload.get("sub"))).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user


# ===== Panel de administracion =====
ADMIN_COOKIE = "admin_token"


def _create_admin_token() -> str:
    return create_access_token({"sub": "admin", "role": "admin"},
                               expires_delta=timedelta(hours=12))


def require_admin(request: Request) -> bool:
    token = request.cookies.get(ADMIN_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="No autorizado")
    payload = decode_token(token)
    if not payload or payload.get("role") != "admin":
        raise HTTPException(status_code=401, detail="No autorizado")
    return True


def _user_row(u: User) -> dict:
    return {
        "id": u.id,
        "email": u.email,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "country": u.country,
        "birth_date": u.birth_date,
        "is_verified": bool(u.is_verified),
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "last_login": u.last_login.isoformat() if u.last_login else None,
        "avatar": u.avatar or f"/api/avatar/default/{u.id}",
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "settings": settings})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "settings": settings})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "settings": settings})


@app.get("/verify", response_class=HTMLResponse)
async def verify_page(request: Request):
    return templates.TemplateResponse("verify.html", {"request": request, "settings": settings})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "settings": settings})


@app.post("/api/register")
async def register(
    email: str = Form(...),
    password: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    country: str = Form(...),
    birth_date: str = Form(...),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    if len(password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")

    code = generate_verification_code()
    user = User(
        email=email,
        hashed_password=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        country=country,
        birth_date=birth_date,
        verification_code=code,
        code_expires_at=code_expiry(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    await send_verification_email(email, code, first_name)

    return {"message": "Registro exitoso. Revisa tu email para el código de verificación.", "email": email}


@app.post("/api/verify")
async def verify_code(
    email: str = Form(...),
    code: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="La cuenta ya está verificada")

    if user.verification_code != code:
        raise HTTPException(status_code=400, detail="Código incorrecto")

    if user.code_expires_at and datetime.utcnow() > user.code_expires_at:
        raise HTTPException(status_code=400, detail="El código ha expirado. Solicita uno nuevo.")

    user.is_verified = True
    user.verification_code = None
    user.code_expires_at = None
    db.commit()

    await send_welcome_email(user.email, user.first_name)

    token = create_access_token({"sub": user.id})
    response = JSONResponse({"message": "Cuenta verificada exitosamente", "token": token})
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    return response


@app.post("/api/resend-code")
async def resend_code(
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="La cuenta ya está verificada")

    code = generate_verification_code()
    user.verification_code = code
    user.code_expires_at = code_expiry()
    db.commit()

    await send_verification_email(user.email, code, user.first_name)
    return {"message": "Código reenviado"}


@app.post("/api/login")
async def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Debes verificar tu email antes de iniciar sesión")

    user.last_login = datetime.utcnow()
    db.commit()

    token = create_access_token({"sub": user.id})
    response = JSONResponse({"message": "Login exitoso", "token": token, "user": {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "country": user.country,
        "birth_date": user.birth_date,
    }})
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    return response


@app.post("/api/logout")
async def logout():
    response = JSONResponse({"message": "Sesión cerrada"})
    response.delete_cookie("access_token")
    return response


@app.get("/api/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "country": user.country,
        "birth_date": user.birth_date,
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "avatar": user.avatar or f"/api/avatar/default/{user.id}",
    }


@app.get("/api/avatar/default/{user_id}")
async def default_avatar(user_id: int, db: Session = Depends(get_db)):
    """Avatar determinista y distinto para cada usuario (sin depender de internet)."""
    user = db.query(User).filter(User.id == user_id).first()
    seed = user.email if user else str(user_id)
    h = hashlib.md5(seed.encode("utf-8")).hexdigest()
    hue = int(h[0:6], 16) % 360
    hue2 = (hue + 55) % 360
    first = (user.first_name[:1] if user and user.first_name else "U")
    last = (user.last_name[:1] if user and user.last_name else "")
    initials = (first + last).upper()
    shapes = ""
    for i in range(4):
        cx = 15 + int(h[i * 6:i * 6 + 2], 16) % 100
        cy = 15 + int(h[i * 6 + 2:i * 6 + 4], 16) % 100
        r = 12 + int(h[i * 6 + 4:i * 6 + 6], 16) % 24
        shapes += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="hsla({(hue2 + i * 45) % 360},85%,72%,0.20)"/>'
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="hsl({hue},72%,55%)"/><stop offset="1" stop-color="hsl({hue2},72%,38%)"/></linearGradient></defs>
<rect width="128" height="128" rx="64" fill="url(#g)"/>{shapes}
<text x="64" y="80" text-anchor="middle" font-family="Arial,sans-serif" font-size="46" font-weight="700" fill="#fff" opacity="0.96">{initials}</text></svg>'''
    return Response(svg, media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=86400"})


@app.post("/api/avatar")
async def upload_avatar(file: UploadFile = File(...),
                        user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    allowed = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Formato no permitido. Usa PNG, JPG, WEBP o GIF.")
    content = await file.read()
    if len(content) > 3 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="La imagen debe pesar menos de 3 MB.")
    ext = allowed[file.content_type]
    # Guardar dentro de la base de datos: funciona en hosting sin disco persistente
    user.avatar = "data:image/" + ext + ";base64," + base64.b64encode(content).decode("ascii")
    db.commit()
    return {"avatar": user.avatar}


@app.get("/api/download")
async def download_info(user: User = Depends(get_current_user)):
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Debes verificar tu cuenta primero")
    return {"url": settings.DOWNLOAD_URL, "filename": "TurboxClipsPro.exe"}


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, db: Session = Depends(get_db)):
    # Acceso alternativo por enlace privado (util si el navegador no envia formularios)
    access_key = request.query_params.get("key")
    if access_key and settings.ADMIN_ACCESS_KEY and \
            secrets.compare_digest(access_key, settings.ADMIN_ACCESS_KEY):
        target = "/admin?nojs=1" if request.query_params.get("nojs") == "1" else "/admin"
        response = RedirectResponse(target, status_code=303)
        response.set_cookie(ADMIN_COOKIE, _create_admin_token(), httponly=True,
                            samesite="lax", max_age=60 * 60 * 24 * 30)
        return response

    token = request.cookies.get(ADMIN_COOKIE)
    payload = decode_token(token) if token else None
    authed = bool(payload and payload.get("role") == "admin")
    users = []
    if authed:
        users = [_user_row(u) for u in db.query(User).order_by(User.id.desc()).all()]
    template_name = "admin_nojs.html" if request.query_params.get("nojs") == "1" else "admin.html"
    return templates.TemplateResponse(template_name, {
        "request": request,
        "settings": settings,
        "authed": authed,
        "users": users,
        "error": request.query_params.get("error"),
    })


@app.post("/api/admin/login")
async def admin_login(request: Request, response: Response):
    try:
        data = await request.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    password = str(data.get("password") or "")
    if not secrets.compare_digest(password, settings.ADMIN_PASSWORD):
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    response.set_cookie(ADMIN_COOKIE, _create_admin_token(), httponly=True,
                        samesite="lax", max_age=60 * 60 * 12)
    return {"ok": True}


@app.post("/admin/login")
async def admin_login_form(request: Request, password: str = Form("")):
    """Respaldo sin JavaScript: si el JS falla, el formulario sigue funcionando."""
    if not secrets.compare_digest(password, settings.ADMIN_PASSWORD):
        return RedirectResponse("/admin?error=1", status_code=303)
    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie(ADMIN_COOKIE, _create_admin_token(), httponly=True,
                        samesite="lax", max_age=60 * 60 * 12)
    return response


@app.post("/api/admin/logout")
async def admin_logout(response: Response):
    response.delete_cookie(ADMIN_COOKIE)
    return {"ok": True}


@app.post("/admin/logout")
async def admin_logout_form():
    response = RedirectResponse("/admin", status_code=303)
    response.delete_cookie(ADMIN_COOKIE)
    return response


@app.get("/api/admin/session")
async def admin_session(request: Request):
    token = request.cookies.get(ADMIN_COOKIE)
    payload = decode_token(token) if token else None
    return {"ok": bool(payload and payload.get("role") == "admin")}


@app.get("/api/admin/users")
async def admin_users(db: Session = Depends(get_db),
                      authorized: bool = Depends(require_admin)):
    users = db.query(User).order_by(User.id.desc()).all()
    return {"users": [_user_row(u) for u in users]}


@app.post("/api/admin/users/{user_id}/verify")
async def admin_toggle_verify(user_id: int, db: Session = Depends(get_db),
                              authorized: bool = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user.is_verified = not bool(user.is_verified)
    if user.is_verified:
        user.verification_code = None
        user.code_expires_at = None
    db.commit()
    return {"ok": True, "is_verified": bool(user.is_verified)}


@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(user_id: int, db: Session = Depends(get_db),
                            authorized: bool = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    for old in AVATARS_DIR.glob(f"avatar_{user_id}.*"):
        old.unlink(missing_ok=True)
    db.delete(user)
    db.commit()
    return {"ok": True}


@app.post("/admin/users/{user_id}/verify")
async def admin_toggle_verify_form(user_id: int, request: Request,
                                   db: Session = Depends(get_db),
                                   authorized: bool = Depends(require_admin)):
    await admin_toggle_verify(user_id, db, authorized)
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/users/{user_id}/delete")
async def admin_delete_user_form(user_id: int, request: Request,
                                 db: Session = Depends(get_db),
                                 authorized: bool = Depends(require_admin)):
    await admin_delete_user(user_id, db, authorized)
    return RedirectResponse("/admin", status_code=303)


@app.get("/api/admin/export")
async def admin_export(db: Session = Depends(get_db),
                       authorized: bool = Depends(require_admin)):
    users = db.query(User).order_by(User.id).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "Email", "Nombre", "Apellido", "Pais",
                     "Fecha nacimiento", "Verificado", "Registro", "Ultimo login"])
    for u in users:
        writer.writerow([
            u.id, u.email, u.first_name, u.last_name, u.country, u.birth_date,
            "Si" if u.is_verified else "No",
            u.created_at.isoformat(sep=" ") if u.created_at else "",
            u.last_login.isoformat(sep=" ") if u.last_login else "",
        ])
    content = "\ufeff" + buf.getvalue()
    return Response(content, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition":
                             'attachment; filename="registros_turboxclips.csv"'})


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
