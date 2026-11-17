import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    # Segurança
    SECRET_KEY = os.getenv("SECRET_KEY")

    # Sessão: cookie protegido e expira por inatividade
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # mude para True quando usar HTTPS
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # Banco de dados (MariaDB)
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME")

    # Uploads (pasta privada, fora de static/)
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    MAX_CONTENT_LENGTH = 512 * 1024 * 1024  # 512 MB por requisição
    LIMITE_FOTO_MB = 15
    LIMITE_VIDEO_MB = 300
    EXTENSOES_FOTO = {"jpg", "jpeg", "png", "webp"}
    EXTENSOES_VIDEO = {"mp4", "mov", "webm"}

    # CSRF
    WTF_CSRF_TIME_LIMIT = None  # o token vale enquanto a sessão durar