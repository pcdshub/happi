"""
Backend implemenation using the ``simplejson`` package.
"""
import contextlib
import logging
import math
import os
import os.path
import re
import shutil
import uuid
from typing import Any, Callable, Optional, Union

import simplejson as json

from .. import utils
from ..errors import DuplicateError, SearchError
from .core import ItemMeta, ItemMetaGen, _Backend

logger = logging.getLogger(__name__)

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
    initialize : bool, optional
        Initialize a new empty JSON file to begin filling.
    cfg_path : str, optional
        Path to the happi config.
    """

    def __init__(
        self,
        path: str,
        initialize: bool = False,
        cfg_path: Optional[str] = None
    ) -> None:
        self._load_cache: dict[str, ItemMeta] = None
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

    def _load_or_initialize(self) -> Optional[dict[str, ItemMeta]]:
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
    def all_items(self) -> list[ItemMeta]:
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

    def load(self) -> dict[str, ItemMeta]:
        """Load the JSON database."""
        with open(self.path) as f:
            raw_json = f.read()

        # Allow for empty files to be considered valid databases:
        return json.loads(raw_json) if raw_json else {}

    def store(self, db: dict[str, ItemMeta]) -> None:
        """
        Stash the database in the JSON file.

        This is a two-step process:

        1. Write the database out to a temporary file
        2. Move the temporary file over the previous database.

        Step 2 is an atomic operation, ensuring that the database
        does not get corrupted by an interrupted json.dump.

        Parameters
        ----------
        db : dict
            Dictionary to store in JSON.
        """
        temp_path = self._temp_path()
        try:
            with open(temp_path, 'w') as fd:
                json.dump(db, fd, sort_keys=True, indent=4)

            if os.path.exists(self.path):
                shutil.copymode(self.path, temp_path)
            shutil.move(temp_path, self.path)
        except BaseException as ex:
            logger.debug('JSON db move failed: %s', ex, exc_info=ex)
            # remove temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def _temp_path(self) -> str:
        """
        Return a temporary path to write the json file to during "store".

        Includes a hash for uniqueness
        (in the cases where multiple temp files are written at once).
        """
        directory = os.path.dirname(self.path)
        filename = (
            f"_{str(uuid.uuid4())[:8]}"
            f"_{os.path.basename(self.path)}"
        )
        return os.path.join(directory, filename)

    def _iterative_compare(self, comparison: Callable) -> ItemMetaGen:
        """
        Yields documents in which ``comparison(name, doc)`` returns `True`.

        Parameters
        ----------
        comparison : Callable
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

    def get_by_id(self, id_: str) -> ItemMeta:
        """Get an item by ID if it exists, or return None."""
        db = self._load_or_initialize()
        return db.get(id_)

    def find(self, to_match: dict[str, Any]) -> ItemMetaGen:
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

    def find_range(
        self,
        key: str,
        *,
        start: Union[int, float],
        stop: Optional[Union[int, float]] = None,
        to_match: dict[str, Any]
    ) -> ItemMetaGen:
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

    def find_regex(
        self,
        to_match: dict[str, Any],
        *,
        flags=re.IGNORECASE
    ) -> ItemMetaGen:
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

    def save(
        self,
        _id: str,
        post: dict[str, Any],
        insert: bool = True
    ) -> None:
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
                    raise SearchError(f"No item found {_id}")

    def delete(self, _id: str) -> None:
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
