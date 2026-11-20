import aiosmtplib
from email.message import EmailMessage
from typing import Optional

from .config import settings


async def send_verification_email(to_email: str, code: str, first_name: str) -> bool:
    if not settings.SMTP_USER or not settings.SMTP_PASS:
        print("=" * 60)
        print(f"[DEV] SMTP no configurado. Codigo de verificacion para {to_email}: {code}")
        print("=" * 60)
        return True

    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = f"{settings.APP_NAME} - Código de verificación"
    msg.set_content(f"""
Hola {first_name},

Tu código de verificación es: {code}

Este código expira en {settings.VERIFICATION_CODE_EXPIRE_MINUTES} minutos.

Si no solicitaste este registro, ignora este mensaje.

Saludos,
{settings.APP_NAME}
""")

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            start_tls=True,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASS,
        )
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        print(f"[DEV] Código para {to_email}: {code}")
        return False


async def send_welcome_email(to_email: str, first_name: str) -> bool:
    if not settings.SMTP_USER or not settings.SMTP_PASS:
        print(f"[EMAIL] Bienvenida para {to_email}")
        return True

    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = f"Bienvenido a {settings.APP_NAME}"
    msg.set_content(f"""
Hola {first_name},

Tu cuenta ha sido verificada exitosamente.

Ya puedes descargar el programa desde tu panel de usuario.

Saludos,
{settings.APP_NAME}
""")

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            start_tls=True,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASS,
        )
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False
