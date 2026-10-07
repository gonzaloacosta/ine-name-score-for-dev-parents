"""Local preview: API + static frontend on one port. Not used on Vercel.

uv run uvicorn serve_local:app --app-dir scripts --reload
"""

from pathlib import Path

from fastapi.staticfiles import StaticFiles

from name_selector.api import app

app.mount("/", StaticFiles(directory=Path(__file__).resolve().parent.parent / "public", html=True))
