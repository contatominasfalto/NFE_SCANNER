import os
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./nfe_scanner.db")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BACKEND_DIR / "uploads"))
REPORT_DIR = os.getenv("REPORT_DIR", str(BACKEND_DIR / "reports"))
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "/usr/bin/tesseract")

# Criar diretórios se não existirem
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)
