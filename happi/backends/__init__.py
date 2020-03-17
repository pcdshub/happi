__all__ = ['backend', 'BACKENDS', 'DEFAULT_BACKEND']
import os

def _get_backend(backend):
    if backend == 'mongodb':
        from .mongo_db import MongoBackend
        return MongoBackend
    if backend == 'json':
        from .json_db import JSONBackend
        return JSONBackend
    raise ValueError(f'Unknown backend {backend!r}')


def _get_backends():
    # A hook for entrypoints or something similar later
    backends = {}
    try:
        backends['json'] = _get_backend('json')
    except ImportError as ex:
        logger.warning('JSON backend unavailable: %s', ex)

    try:
        backends['mongodb'] = _get_backend('mongodb')
    except ImportError as ex:
        logger.warning('MongoDB backend unavailable: %s', ex)

    return backends


BACKENDS = _get_backends()
try:
    # Check to see if the user has specified a specific backend as an
    # environment variable. Import this as the standard backend for other
    # places in the module. A user can always override this by explicitly
    # importing the backend
    DEFAULT_BACKEND = BACKENDS[os.environ.get("HAPPI_BACKEND", 'json').lower()]
except KeyError:
    raise ImportError("Improper specification of happi backend. "
                      "Check the `$HAPPI_BACKEND` environment variable.")

# back-compatibility
backend = DEFAULT_BACKEND
