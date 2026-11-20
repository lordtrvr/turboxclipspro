import base64
import json
import urllib.parse
import urllib.request
import urllib.error

import aiosmtplib
from email.message import EmailMessage
from typing import Optional

from .config import settings


def _gmail_send(to_email: str, subject: str, body: str) -> bool:
    """Envia correo via Gmail API (HTTPS puerto 443 - funciona en Render free)."""
    client_id = getattr(settings, "GMAIL_CLIENT_ID", None)
    client_secret = getattr(settings, "GMAIL_CLIENT_SECRET", None)
    refresh_token = getattr(settings, "GMAIL_REFRESH_TOKEN", None)
    sender = getattr(settings, "GMAIL_SENDER", None) or "turboxclips@gmail.com"
    if not (client_id and client_secret and refresh_token):
        return False
    try:
        # 1. Obtener access token
        data = urllib.parse.urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://oauth2.googleapis.com/token", data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            access = json.loads(resp.read().decode("utf-8"))["access_token"]

        # 2. Construir mensaje MIME
        message = (
            f"From: {sender}\r\n"
            f"To: {to_email}\r\n"
            f"Subject: {subject}\r\n"
            "Content-Type: text/plain; charset=utf-8\r\n\r\n"
            f"{body}\r\n"
        )
        raw = base64.urlsafe_b64encode(message.encode("utf-8")).decode("ascii")
        payload = json.dumps({"raw": raw}).encode("utf-8")
        req2 = urllib.request.Request(
            f"https://gmail.googleapis.com/gmail/v1/users/{sender}/messages/send",
            data=payload,
            headers={"Authorization": f"Bearer {access}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req2, timeout=20) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:
        print(f"[GMAIL ERROR] HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}")
        return False
    except Exception as e:
        print(f"[GMAIL ERROR] {e}")
        return False


def _send_via_resend(to_email: str, subject: str, body: str) -> bool:
    """Envia email mediante la API HTTP de Resend (respaldo)."""
    api_key = getattr(settings, "RESEND_API_KEY", None)
    if not api_key:
        return False
    from_email = getattr(settings, "RESEND_FROM", None) or "onboarding@resend.dev"
    if "resend.dev" in from_email or not from_email:
        from_email = "onboarding@resend.dev"
    payload = {"from": from_email, "to": [to_email], "subject": subject, "text": body}
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:
        print(f"[RESEND ERROR] HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}")
        return False
    except Exception as e:
        print(f"[RESEND ERROR] {e}")
        return False


async def _send_via_smtp(to_email: str, subject: str, body: str) -> bool:
    """Respaldo SMTP (bloqueado en Render free)."""
    if not settings.SMTP_USER or not settings.SMTP_PASS:
        return False
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        await aiosmtplib.send(
            msg, hostname=settings.SMTP_HOST, port=settings.SMTP_PORT,
            start_tls=True, username=settings.SMTP_USER,
            password=settings.SMTP_PASS, timeout=10)
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


def _verification_body(first_name: str, code: str) -> str:
    return f"""Hola {first_name},

Tu codigo de verificacion es: {code}

Este codigo expira en {settings.VERIFICATION_CODE_EXPIRE_MINUTES} minutos.

Si no solicitaste este registro, ignora este mensaje.

Saludos,
{settings.APP_NAME}
"""


async def send_verification_email(to_email: str, code: str, first_name: str) -> bool:
    subject = f"{settings.APP_NAME} - Codigo de verificacion"
    body = _verification_body(first_name, code)

    if _gmail_send(to_email, subject, body):
        print(f"[EMAIL] Verificacion enviada por Gmail a {to_email}")
        return True
    if _send_via_resend(to_email, subject, body):
        print(f"[EMAIL] Verificacion enviada por Resend a {to_email}")
        return True
    if await _send_via_smtp(to_email, subject, body):
        print(f"[EMAIL] Verificacion enviada por SMTP a {to_email}")
        return True

    print("=" * 60)
    print(f"[DEV] Sin proveedor de email. Codigo para {to_email}: {code}")
    print("=" * 60)
    return False


async def send_welcome_email(to_email: str, first_name: str) -> bool:
    subject = f"Bienvenido a {settings.APP_NAME}"
    body = f"""Hola {first_name},

Tu cuenta ha sido verificada exitosamente.

Ya puedes descargar el programa desde tu panel de usuario.

Saludos,
{settings.APP_NAME}
"""
    if _gmail_send(to_email, subject, body):
        return True
    if _send_via_resend(to_email, subject, body):
        return True
    if await _send_via_smtp(to_email, subject, body):
        return True
    print(f"[EMAIL] Bienvenida (no enviada) para {to_email}")
    return False
