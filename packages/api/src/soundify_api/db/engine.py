"""SQLite database engine setup."""

from pathlib import Path

from sqlalchemy import Engine
from sqlmodel import create_engine


def create_db_engine(db_path: Path) -> Engine:
    """Create SQLite engine.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        SQLAlchemy engine configured for SQLite.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
