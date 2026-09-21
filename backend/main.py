"""
Main entry point for Honey Chain / Madhu Sathi backend.
Exports the FastAPI application instance for Vercel, Uvicorn, and Gunicorn.
"""

from app.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
