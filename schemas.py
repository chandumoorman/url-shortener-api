# schemas.py
# Pydantic models — define the shape of data coming IN and going OUT of the API.
# NEVER return SQLAlchemy model objects directly from routes. Always use these.
# Why: controls exactly what data is exposed, auto-validates input, auto-documents API.

from pydantic import BaseModel, HttpUrl, field_validator
from datetime import datetime
from typing import Optional

# ──────────────────────────────────────────
# REQUEST SCHEMAS (client → API)
# ──────────────────────────────────────────

class URLCreate(BaseModel):
    # HttpUrl validates format automatically.
    # "not-a-url" → FastAPI returns 422 Unprocessable Entity before your code runs.
    original_url: HttpUrl

    @field_validator("original_url", mode="before")
    @classmethod
    def strip_whitespace(cls, v):
        # Clean up URLs like "  https://google.com  " with accidental spaces
        return str(v).strip() if isinstance(v, str) else v


# ──────────────────────────────────────────
# RESPONSE SCHEMAS (API → client)
# ──────────────────────────────────────────

class URLResponse(BaseModel):
    short_code: str
    short_url: str          # Constructed full URL: "http://localhost:8000/aB3xYz"
    original_url: str
    created_at: datetime
    click_count: int

    # from_attributes=True → Pydantic can read data from SQLAlchemy ORM objects
    # (which use attribute access) not just plain dicts.
    # Without this, response_model= in route decorators won't work.
    model_config = {"from_attributes": True}


class URLStats(BaseModel):
    short_code: str
    original_url: str
    click_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ErrorResponse(BaseModel):
    detail: str
    status_code: int