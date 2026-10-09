"""
Database engine/session management.

The connection URL comes from the DATABASE_URL environment variable and
defaults to a local SQLite file, so the project works out of the box.
Switching to PostgreSQL only requires changing the URL, e.g.:

    DATABASE_URL=postgresql+psycopg2://user:pass@db:5432/sentinel
"""
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.models import Base

DEFAULT_URL = "sqlite:///data/sentinel.db"

_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_URL)


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        url = get_database_url()
        kwargs = {"future": True, "pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
            # Make sure the directory for a file-based SQLite DB exists.
            if ":memory:" not in url:
                db_path = url.split("///", 1)[-1]
                if db_path:
                    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(url, **kwargs)

        if url.startswith("sqlite"):
            @event.listens_for(_engine, "connect")
            def _sqlite_pragmas(dbapi_conn, _):  # pragma: no cover - trivial
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA journal_mode=WAL")
                cur.execute("PRAGMA foreign_keys=ON")
                cur.close()

        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def reset_engine() -> None:
    """Dispose the cached engine (used by tests and after DATABASE_URL changes)."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def init_db() -> None:
    """Create all tables if they do not exist yet (idempotent)."""
    Base.metadata.create_all(get_engine())


@contextmanager
def get_session() -> Iterator[Session]:
    """Transactional session: commits on success, rolls back on error."""
    get_engine()
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
