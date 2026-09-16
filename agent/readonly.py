"""SQLite execution boundary, independent of the SQL parser."""
from pathlib import Path
import sqlite3
import time

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from .guard import SQLITE_FUNCTIONS


def readonly_engine(db_url):
    url = make_url(db_url)
    if url.drivername not in ('sqlite', 'sqlite+pysqlite') or not url.database or url.database == ':memory:':
        raise ValueError('This demo supports an existing, file-backed SQLite database only.')
    if url.query:
        raise ValueError('SQLite URL query options are not supported.')
    path = Path(url.database).resolve(strict=True)

    def connect():
        conn = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=2, cached_statements=0)
        conn.execute('PRAGMA query_only=ON')
        return conn

    return create_engine('sqlite://', creator=connect, poolclass=NullPool)


def restrict_connection(conn, allowed_tables, timeout_seconds):
    """Call after introspection, before executing any model-generated SQL."""
    allowed = {name.casefold() for name in allowed_tables}

    def authorize(action, arg1, arg2, db_name, trigger):
        if action == sqlite3.SQLITE_SELECT:
            return sqlite3.SQLITE_OK
        # SQLite reports db_name=None for an empty-column table read (COUNT(*)).
        if action == sqlite3.SQLITE_READ and (db_name == 'main' or (db_name is None and arg2 == '')) and (arg1 or '').casefold() in allowed:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_FUNCTION and (arg2 or '').lower() in SQLITE_FUNCTIONS:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    deadline = time.monotonic() + timeout_seconds
    conn.set_authorizer(authorize)
    conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
