import os

# Must be set before any `app` import: Settings() is created at import time.
os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost/test")
os.environ.setdefault("JWT_SECRET", "x" * 40)
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("APP_ENV", "test")
