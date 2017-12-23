__all__ = ['backend']
import os
# Check to see if the user has specified a specific backend
# as an environment variable. Import this as the standard
# backend for other places in the module. A user can always
# override this by explicitly importing the backend
_backend = os.environ.get("HAPPI_BACKEND", '').lower()

if _backend == 'mongodb':
    from .mongo_db import MongoBackend as backend
else:
    from .json_db import JSONBackend as backend

del _backend
