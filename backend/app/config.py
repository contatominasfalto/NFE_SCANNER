import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nfe_scanner.db")
REPORT_DIR = os.getenv("REPORT_DIR", str(BACKEND_DIR / "reports"))
LOG_DIR = os.getenv("LOG_DIR", str(BACKEND_DIR / "logs"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
MEUDANFE_API_BASE_URL = os.getenv(
    "MEUDANFE_API_BASE_URL",
    "https://api.meudanfe.com.br/v2/fd/get/xml",
)
MEUDANFE_API_KEY = os.getenv("MEUDANFE_API_KEY", "")

os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
