from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    DATABASE_URL: str = "sqlite:///./turbox_web.db"

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    SMTP_FROM: Optional[str] = None

    # Resend (API HTTP - funciona en Render free; SMTP está bloqueado)
    RESEND_API_KEY: Optional[str] = None
    RESEND_FROM: Optional[str] = None

    APP_NAME: str = "TurboxClipsPro"
    APP_URL: str = "http://localhost:8000"
    DOWNLOAD_URL: str = "/downloads/TurboxClipsPro.exe"
    ADMIN_WHATSAPP: str = "521234567890"
    VERIFICATION_CODE_EXPIRE_MINUTES: int = 15

    # Panel de administracion (separado de las cuentas de usuario)
    ADMIN_PASSWORD: str = "cambiar-admin"
    ADMIN_ACCESS_KEY: str = ""

    # Origen del frontend en Netlify (para CORS). Separar varios con coma.
    FRONTEND_URL: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
