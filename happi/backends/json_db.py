"""
Backend implemenation using the ``simplejson`` package.
"""
import contextlib
import logging
import math
import os
import os.path
import re
from typing import Any, Dict, Optional

import simplejson as json

from .. import utils
from ..errors import DuplicateError, SearchError
from .core import _Backend

logger = logging.getLogger(__name__)


try:
    import fcntl
except ImportError:
    logger.debug("Unable to import 'fcntl'. Will be unable to lock files")
    fcntl = None


# A sentinel for keys that are missing for comparisons below.
_MISSING = object()


@contextlib.contextmanager
def _load_and_store_context(backend):
    """Context manager used to load, and optionally store the JSON database."""
    db = backend._load_or_initialize()
    yield db
    backend.store(db)


class JSONBackend(_Backend):
    """
    JSON database.

    The happi information is kept in a single large dictionary that is stored
    using the ``simplejson`` package.

    Parameters
    ----------
    path : str
        Path to JSON file.
    initialze : bool, optional
        Initialize a new empty JSON file to begin filling.
    cfg_path : str, optional
        Path to the happi config.
    """

    def __init__(self, path: str, initialize: bool = False, cfg_path: Optional[str] = None):
        self._load_cache = None
        # Determine the cfg dir and build path to json db based on that unless we're initted w/o a config
        if cfg_path is not None:
            cfg_dir = os.path.dirname(cfg_path)
            self.path = utils.build_abs_path(cfg_dir, path)
        else:
            self.path = path
        # Create a new JSON file if requested
        if initialize:
            self.initialize()

    def clear_cache(self) -> None:
        """Clear the loaded cache."""
        self._load_cache = None

    def _load_or_initialize(self):
        """Load an existing database or initialize a new one."""
        if self._load_cache is None:
            try:
                self._load_cache = self.load()
            except FileNotFoundError:
                logger.debug("Initializing new database")
                self.initialize()
                self._load_cache = self.load()

        return self._load_cache

    @property
    def all_items(self):
        """All of the items in the database."""
        json = self._load_or_initialize()
        return list(json.values())

    def initialize(self):
        """
        Initialize a new JSON file database.

        Raises
        ------
        PermissionError
            If the JSON file specified by ``path`` already exists.

        Notes
        -----
        This exists because the `.store` and `.load` methods assume that the
        given path already points to a readable JSON file. In order to begin
        filling a new database, an empty but valid JSON file is created.
        """

        # Do not overwrite existing databases
        if os.path.exists(self.path) and os.stat(self.path).st_size > 0:
            raise PermissionError("File {} already exists. Can not initialize "
                                  "a new database.".format(self.path))
        # Dump an empty dictionary
        self.store({})

    def load(self):
        """Load the JSON database."""
        with open(self.path, 'r') as f:
            raw_json = f.read()

        # Allow for empty files to be considered valid databases:
        return json.loads(raw_json) if raw_json else {}

    def store(self, db):
        """
        Stash the database in the JSON file.

        Parameters
        ----------
        db : dict
            Dictionary to store in JSON.

        Raises
        ------
        BlockingIOError
            If the file is already being used by another happi operation.
        """

        with open(self.path, 'w+') as f:
            # Create lock in filesystem
            if fcntl is not None:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Dump to file
            try:
                json.dump(db, f, sort_keys=True, indent=4)

            finally:
                if fcntl is not None:
                    # Release lock in filesystem
                    fcntl.flock(f, fcntl.LOCK_UN)

    def _iterative_compare(self, comparison):
        """
        Yields documents in which ``comparison(name, doc)`` returns `True`.

        Parameters
        ----------
        comparison : callable
            A comparison function with a signature of (item_id, doc).
        """

        db = self._load_or_initialize()
        if not db:
            return

        for name, doc in db.items():
            try:
                if comparison(name, doc):
                    yield doc
            except Exception as ex:
                logger.debug('Comparison method failed: %s', ex, exc_info=ex)

    def get_by_id(self, id_):
        """Get an item by ID if it exists, or return None."""
        db = self._load_or_initialize()
        return db.get(id_)

    def find(self, to_match):
        """
        Find an instance or instances that matches the search criteria.

        Parameters
        ----------
        to_match : dict
            Requested information, all of which must match.
        """

        def comparison(name, doc):
            return all(
                value == doc.get(key, _MISSING)
                for key, value in to_match.items()
            )

        yield from self._iterative_compare(comparison)

    def find_range(self, key, *, start, stop=None, to_match):
        """
        Find an instance or instances that matches the search criteria, such
        that ``start <= entry[key] < stop``.

        Parameters
        ----------
        key : str
            The database key to search.
        start : int or float
            Inclusive minimum value to filter ``key`` on.
        end : float, optional
            Exclusive maximum value to filter ``key`` on.
        to_match : dict
            Requested information, where the values must match exactly.
        """

        def comparison(name, doc):
            if all(value == doc.get(k, _MISSING)
                   for k, value in to_match.items()):
                try:
                    return start <= doc[key] < stop
                except Exception:
                    ...
            return False

        if key in to_match:
            raise ValueError('Cannot specify the same key in `to_match` as '
                             'the key for the range.')
        if stop is None:
            stop = math.inf
        if start >= stop:
            raise ValueError(f"Invalid range: {start} >= {stop}")

        yield from self._iterative_compare(comparison)

    def find_regex(self, to_match, *, flags=re.IGNORECASE):
        """
        Find an instance or instances that matches the search criteria,
        using regular expressions.

        Parameters
        ----------
        to_match : dict
            Requested information, where the values are regular expressions.
        """

        def comparison(name, doc):
            return regexes and all(key in doc and regex.match(str(doc[key]))
                                   for key, regex in regexes.items())

        regexes = {
            key: re.compile(value, flags=flags)
            for key, value in to_match.items()
        }

        yield from self._iterative_compare(comparison)

    def save(self, _id: str, post: Dict[str, Any], insert: bool = True):
        """
        Save information to the database.

        Parameters
        ----------
        _id : str
            ID of item.
        post : dict
            Information to place in database.
        insert : bool, optional
            Whether or not this is a new item to the database.

        Raises
        ------
        DuplicateError
            If ``insert`` is `True`, but there is already an item with the
            provided ``_id``.
        SearchError
            If ``insert`` is `False`, but there is no item with the provided
            ``_id``.
        PermissionError
            If the write operation fails due to issues with permissions.
        """

        with _load_and_store_context(self) as db:
            # New item
            if insert:
                if _id in db.keys():
                    raise DuplicateError(f"Item {_id} already exists")
                # Add _id keyword
                post.update({'_id': _id})
                # Add to database
                db[_id] = post
            # Updating item
            else:
                # Edit information
                try:
                    db[_id].update(post)
                except KeyError:
                    raise SearchError("No item found {}".format(_id))

    def delete(self, _id: str):
        """
        Delete an item instance from the database.

        Parameters
        ----------
        _id : str
            ID of item.

        Raises
        ------
        PermissionError
            If the write operation fails due to issues with permissions.
        """

        with _load_and_store_context(self) as db:
            try:
                db.pop(_id)
            except KeyError:
                raise SearchError(
                    f'ID not found in database: {_id!r}'
                ) from None
