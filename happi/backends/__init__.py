__all__ = ['backend']
import os
# Check to see if the user has specified a specific backend
# as an environment variable. Import this as the standard
# backend for other places in the module. A user can always
# override this by explicitly importing the backend
_backend = os.environ.get("HAPPI_BACKEND", 'json').lower()


def _get_backend(backend):
    if backend == 'mongodb':
        from .mongo_db import MongoBackend
        return MongoBackend
    elif backend == 'json':
        from .json_db import JSONBackend
        return JSONBackend
    else:
        raise ImportError("Improper specification of happi backend."
                          "Check `$HAPPI_BACKEND` environment variable.")


backend = _get_backend(_backend)

del _backend
