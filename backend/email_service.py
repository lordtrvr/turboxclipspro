import json
import urllib.request
import urllib.error

import aiosmtplib
from email.message import EmailMessage
from typing import Optional

from .config import settings


def _send_via_resend(to_email: str, subject: str, body: str) -> bool:
    """Envía email mediante la API HTTP de Resend (puerto 443, permitido en Render)."""
    api_key = getattr(settings, "RESEND_API_KEY", None)
    if not api_key:
        return False
    from_email = getattr(settings, "RESEND_FROM", None) or "TurboxClipsPro <onboarding@resend.dev>"
    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "text": body,
    }
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        print(f"[RESEND ERROR] HTTP {e.code}: {detail}")
        return False
    except Exception as e:
        print(f"[RESEND ERROR] {e}")
        return False


async def _send_via_smtp(to_email: str, subject: str, body: str) -> bool:
    """Respaldo SMTP (funciona en local / planes pagos; bloqueado en Render free)."""
    if not settings.SMTP_USER or not settings.SMTP_PASS:
        return False
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            start_tls=True,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASS,
            timeout=10,
        )
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


def _verification_body(first_name: str, code: str) -> str:
    return f"""
Hola {first_name},

Tu código de verificación es: {code}

Este código expira en {settings.VERIFICATION_CODE_EXPIRE_MINUTES} minutos.

Si no solicitaste este registro, ignora este mensaje.

Saludos,
{settings.APP_NAME}
"""


async def send_verification_email(to_email: str, code: str, first_name: str) -> bool:
    subject = f"{settings.APP_NAME} - Código de verificación"
    body = _verification_body(first_name, code)

    # 1) Preferir API HTTP (funciona en Render free)
    if _send_via_resend(to_email, subject, body):
        print(f"[EMAIL] Verificación enviada por Resend a {to_email}")
        return True

    # 2) Respaldo SMTP
    if await _send_via_smtp(to_email, subject, body):
        print(f"[EMAIL] Verificación enviada por SMTP a {to_email}")
        return True

    # 3) Modo desarrollo: imprimir el código
    print("=" * 60)
    print(f"[DEV] SMTP/Resend no disponibles. Código para {to_email}: {code}")
    print("=" * 60)
    return False


async def send_welcome_email(to_email: str, first_name: str) -> bool:
    subject = f"Bienvenido a {settings.APP_NAME}"
    body = f"""
Hola {first_name},

Tu cuenta ha sido verificada exitosamente.

Ya puedes descargar el programa desde tu panel de usuario.

Saludos,
{settings.APP_NAME}
"""
    if _send_via_resend(to_email, subject, body):
        return True
    if await _send_via_smtp(to_email, subject, body):
        return True
    print(f"[EMAIL] Bienvenida (no enviada) para {to_email}")
    return False
