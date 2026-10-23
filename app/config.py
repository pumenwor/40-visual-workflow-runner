import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - python-dotenv is a declared dependency
    load_dotenv = None

if load_dotenv is not None:
    # README tells users to copy .env.example to .env; actually load it.
    load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./workflow_runner.db")
APP_ENV = os.getenv("APP_ENV", "development")
ENABLE_DEMO_NODE = os.getenv("ENABLE_DEMO_NODE", "false").lower() == "true"
MAX_CONCURRENT_RUNS = int(os.getenv("MAX_CONCURRENT_RUNS", "1"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
PORT = int(os.getenv("PORT", "8000"))