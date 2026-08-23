"""
FastAPI entry-point in backend root.
Re-exports `app` from `app.main:app`.
"""

from app.main import app

__all__ = ["app"]
