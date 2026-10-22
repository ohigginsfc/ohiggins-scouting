"""Bounded cache for objective reads in the authenticated portal only."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache, wraps
import hashlib
import json

_enabled = ContextVar('objective_read_cache', default=False)
TTL_SECONDS = 900
MAX_ENTRIES = 128


@contextmanager
def objective_read_scope():
    """Opt in only while rendering scouting pages; workers never enter this scope."""
    token = _enabled.set(True)
    try:
        yield
    finally:
        _enabled.reset(token)


@lru_cache(maxsize=1)
def _reader():
    # Workers do not need to initialize Streamlit or its cache.
    import streamlit as st

    @st.cache_data(ttl=TTL_SECONDS, max_entries=MAX_ENTRIES, show_spinner=False)
    def read(operation, database_scope, args, kwargs, _conn, _function):
        # Connection and function are deliberately excluded from hashing. The
        # operation and actual connection identity are explicit keys instead.
        return _function(_conn, *args, **kwargs)
    return read


def cached_objective_read(function):
    """Cache sports data, never authorization, reports or writes."""
    @wraps(function)
    def guarded(conn, *args, **kwargs):
        if not _enabled.get():
            return function(conn, *args, **kwargs)
        from scouting.portal.security import require_user
        require_user()  # Also on cache hits; account/session checks remain live.
        params = conn.info.get_parameters()
        identity = {key: params.get(key, '') for key in
                    ('host', 'hostaddr', 'port', 'dbname', 'user', 'options')}
        database_scope = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        operation = function.__module__ + '.' + function.__qualname__
        return _reader()(operation, database_scope, args, kwargs, conn, function)
    return guarded
