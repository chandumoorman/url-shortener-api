# crud.py
# All database operations live here. Routes import from here.
# Rule: routes handle HTTP. crud.py handles DB. Never mix them.
# This separation makes testing easy — you can test DB logic without HTTP.

import secrets
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models import URL


def generate_short_code(length: int = 6) -> str:
    # secrets module = cryptographically secure random (unlike random module).
    # token_urlsafe generates URL-safe characters (A-Z, a-z, 0-9, -, _).
    # We slice to desired length since token_urlsafe returns variable length.
    return secrets.token_urlsafe(length)[:length]


def get_url_by_short_code(db: Session, short_code: str) -> URL | None:
    return db.query(URL).filter(URL.short_code == short_code).first()


def get_url_by_original(db: Session, original_url: str) -> URL | None:
    # Lets us return an existing record if the same URL was already shortened.
    # Avoids polluting the DB with duplicate entries.
    return db.query(URL).filter(URL.original_url == original_url).first()


def create_short_url(db: Session, original_url: str) -> URL:
    # Collision handling:
    # With 6 chars from ~64 possible characters = 64^6 ≈ 68 billion combinations.
    # Collision is extremely unlikely, but we handle it correctly anyway.
    # A while loop retries with a new code if the code already exists in DB.
    max_attempts = 10
    for attempt in range(max_attempts):
        short_code = generate_short_code()

        # Check at app level first (faster than hitting DB constraints)
        if get_url_by_short_code(db, short_code):
            continue  # Collision — try a new code

        db_url = URL(original_url=original_url, short_code=short_code)
        db.add(db_url)

        try:
            db.commit()  # Write to DB
        except IntegrityError:
            # Race condition: another request inserted the same code between
            # our check and our insert. Rollback and try again.
            db.rollback()
            continue

        db.refresh(db_url)  # Reload from DB to get server-generated values (id, created_at)
        return db_url

    raise RuntimeError("Failed to generate unique short code after 10 attempts")


def increment_click_count(db: Session, db_url: URL) -> URL:
    db_url.click_count += 1
    db.commit()
    db.refresh(db_url)
    return db_url


def get_all_urls(db: Session, skip: int = 0, limit: int = 100) -> list[URL]:
    # Pagination: skip/limit pattern. Never return unbounded queries in production.
    return db.query(URL).offset(skip).limit(limit).all()


def delete_url(db: Session, short_code: str) -> bool:
    db_url = get_url_by_short_code(db, short_code)
    if not db_url:
        return False
    db.delete(db_url)
    db.commit()
    return True