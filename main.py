# main.py
# FastAPI app entry point. Only HTTP concerns live here:
# routing, request parsing, response formatting, error handling.
# Zero business logic. Zero direct DB queries.

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

import models
import crud
from schemas import URLCreate, URLResponse, URLStats
from database import engine, SessionLocal
from config import settings

# Create all tables defined in models.py on startup.
# Fine for development/SQLite. For production use Alembic migrations instead.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    description="Shorten URLs and track click analytics",
    version="1.0.0",
    docs_url="/docs",     # Swagger UI at /docs
    redoc_url="/redoc",   # ReDoc UI at /redoc
)


# ──────────────────────────────────────────
# DEPENDENCY: DB SESSION
# ──────────────────────────────────────────

def get_db():
    # FastAPI calls this for every request that declares db: Session = Depends(get_db).
    # yield hands the session to the route function.
    # The finally block runs after the route finishes — even if an exception occurred.
    # This guarantees DB connections are always returned to the pool.
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ──────────────────────────────────────────
# GLOBAL EXCEPTION HANDLERS
# ──────────────────────────────────────────

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found", "status_code": 404}
    )

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "status_code": 500}
    )


# ──────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "app": settings.app_name}


@app.post("/shorten", response_model=URLResponse, tags=["URLs"])
def shorten_url(url_data: URLCreate, db: Session = Depends(get_db)):
    """
    Accept a long URL, return a shortened version.
    If the same URL was already shortened, returns the existing record.
    """
    original_url = str(url_data.original_url)

    # Idempotency: same URL → same short code, no duplicate DB rows
    existing = crud.get_url_by_original(db, original_url)
    if existing:
        return {
            **existing.__dict__,
            "short_url": f"{settings.base_url}/{existing.short_code}"
        }

    db_url = crud.create_short_url(db, original_url)
    return {
        **db_url.__dict__,
        "short_url": f"{settings.base_url}/{db_url.short_code}"
    }


@app.get("/stats/{short_code}", response_model=URLStats, tags=["URLs"])
def get_stats(short_code: str, db: Session = Depends(get_db)):
    """
    Return click count and metadata for a short URL.
    Note: this route must be defined BEFORE /{short_code}
    or FastAPI will match "stats" as a short_code.
    """
    db_url = crud.get_url_by_short_code(db, short_code)
    if not db_url:
        raise HTTPException(status_code=404, detail=f"Short code '{short_code}' not found")
    return db_url


@app.get("/all", tags=["URLs"])
def list_all_urls(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """
    List all shortened URLs with pagination.
    skip + limit = standard pagination pattern. Know this cold for interviews.
    """
    urls = crud.get_all_urls(db, skip=skip, limit=limit)
    return [
        {**u.__dict__, "short_url": f"{settings.base_url}/{u.short_code}"}
        for u in urls
    ]


@app.delete("/{short_code}", tags=["URLs"])
def delete_url(short_code: str, db: Session = Depends(get_db)):
    deleted = crud.delete_url(db, short_code)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Short code '{short_code}' not found")
    return {"message": f"Deleted '{short_code}' successfully"}


@app.get("/{short_code}", tags=["Redirect"])
def redirect_to_original(short_code: str, db: Session = Depends(get_db)):
    """
    The core feature. Look up short_code → redirect to original URL.
    307 = Temporary Redirect. Browser re-sends the same HTTP method to the new URL.
    301 = Permanent. Browsers CACHE this — avoid for URL shorteners since
          the mapping could be deleted or updated and cached 301s ignore that.
    """
    db_url = crud.get_url_by_short_code(db, short_code)
    if not db_url:
        raise HTTPException(status_code=404, detail=f"Short code '{short_code}' not found")

    crud.increment_click_count(db, db_url)
    return RedirectResponse(url=db_url.original_url, status_code=307)