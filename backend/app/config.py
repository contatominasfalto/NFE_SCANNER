import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nfe_scanner.db").strip()
if any(token in DATABASE_URL for token in ("SENHA_DO_MYSQL", "SENHA_REAL_DO_MYSQL", "ENHA_DO_MYSQL", "troque_esta_senha")):
    raise RuntimeError("DATABASE_URL contem senha de exemplo. Configure a senha real do banco no backend/.env.")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)
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
