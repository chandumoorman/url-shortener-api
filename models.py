# models.py
# Defines DB tables as Python classes.
# One class = one table. Column types map to SQL data types.

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base

class URL(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, index=True)

    # The full original URL (e.g. https://very-long-website.com/article/123)
    original_url = Column(String, nullable=False)

    # The 6-char code we generate (e.g. "aB3xYz")
    # index=True is CRITICAL — every redirect does a lookup on this column.
    # Without an index: O(n) full table scan. With index: O(log n) B-tree lookup.
    # unique=True enforces uniqueness at DB level, not just app level.
    short_code = Column(String, unique=True, index=True, nullable=False)

    # server_default=func.now() → the DB sets this timestamp, not Python.
    # More reliable than Python's datetime.now() which depends on app server time.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Tracks how many times this short URL was redirected
    click_count = Column(Integer, default=0, nullable=False)

    def __repr__(self):
        return f"<URL short_code={self.short_code} original={self.original_url[:30]}>"