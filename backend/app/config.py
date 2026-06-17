import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nfe_scanner.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if DATABASE_URL.startswith("sqlite:///./"):
    database_name = DATABASE_URL.removeprefix("sqlite:///./")
    DATABASE_URL = f"sqlite:///{(BACKEND_DIR / database_name).as_posix()}"

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
MEUDANFE_API_BASE_URL = os.getenv(
    "MEUDANFE_API_BASE_URL",
    "https://api.meudanfe.com.br/v2/fd/get/xml",
)
MEUDANFE_API_KEY = os.getenv("MEUDANFE_API_KEY", "")
SECRET_KEY = os.getenv("SECRET_KEY", "nfe_scanner_default_secret_2026")
