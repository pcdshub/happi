"""
Backend implemenation using simplejson
"""
import contextlib
import os
import os.path
import logging
import math
import re

import simplejson as json

from .core import _Backend
from ..errors import SearchError, DuplicateError

logger = logging.getLogger(__name__)


try:
    import fcntl
except ImportError:
    logger.warning("Unable to import 'fcntl'. Will be unable to lock files")
    fcntl = None


@contextlib.contextmanager
def _load_and_store_context(backend):
    '''
    A context manager to load, and optionally store the JSON database at the
    end
    '''
    db = backend._load_or_initialize()
    yield db
    backend.store(db)


class JSONBackend(_Backend):
    """
    JSON database

    The happi information is kept in a single dictionary large dictionary that
    is stored using `simplejson`

    Parameters
    ----------
    path : str
        Path to JSON file

    initialze : bool, optional
        Initialize a new empty JSON file to begin filling
    """
    def __init__(self, path, initialize=False):
        self.path = path
        # Create a new JSON file if requested
        if initialize:
            self.initialize()

    def _load_or_initialize(self):
        '''
        Load an existing database or initialize a new one.
        '''
        try:
            return self.load()
        except FileNotFoundError:
            logger.debug('Initializing new database')

        self.initialize()
        return self.load()

    @property
    def all_devices(self):
        """
        All of the devices in the database
        """
        json = self._load_or_initialize()
        return list(json.values())

    def initialize(self):
        """
        Initialize a new JSON file database

        Raises
        ------
        PermissionError:
            If the JSON file specified by `path` already exists

        Notes
        -----
        This is exists because the `store` and `load` methods assume that the
        given path already points to a readable JSON file. In order to begin
        filling a new database, an empty but valid JSON file is created
        """
        # Do not overwrite existing databases
        if os.path.exists(self.path) and os.stat(self.path).st_size > 0:
            raise PermissionError("File {} already exists. Can not initialize "
                                  "a new database.".format(self.path))
        # Dump an empty dictionary
        self.store({})

    def load(self):
        """
        Load the JSON database
        """
        with open(self.path, 'r') as f:
            raw_json = f.read()

        # Allow for empty files to be considered valid databases:
        return json.loads(raw_json) if raw_json else {}

    def store(self, db):
        """
        Stache the database back into JSON

        Parameters
        ----------
        db : dict
            Dictionary to store in JSON

        Raises
        ------
        BlockingIOError:
            If the file is already being used by another happi operation
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
        Yields documents in which ``comparison(name, doc)`` returns True.

        Parameters
        ----------
        comparison : callable
            A comparison function with a signature of (device_id, doc)
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
        '''
        Get a device by ID if it exists, or None

        Parameters
        ----------
        id_
        '''
        db = self._load_or_initialize()
        return db.get(id_)

    def find(self, to_match):
        """
        Find an instance or instances that matches the search criteria

        Parameters
        ----------
        to_match : dict
            Requested information, all of which must match
        """
        def comparison(name, doc):
            return all(value == doc[key]
                       for key, value in to_match.items())

        yield from self._iterative_compare(comparison)

    def find_range(self, key, *, start, stop=None, to_match):
        """
        Find an instance or instances that matches the search criteria, such
        that ``start <= entry[key] < stop``.

        Parameters
        ----------
        key : str
            The database key to search

        start : int or float
            Inclusive minimum value to filter ``key`` on

        end : float, optional
            Exclusive maximum value to filter ``key`` on

        to_match : dict
            Requested information, where the values must match exactly
        """
        def comparison(name, doc):
            if all(value == doc[k] for k, value in to_match.items()):
                value = doc.get(key)
                try:
                    return start <= value < stop
                except Exception:
                    ...

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
            return regexes and all(key in doc and regex.match(doc[key])
                                   for key, regex in regexes.items())

        regexes = {
            key: re.compile(value, flags=flags)
            for key, value in to_match.items()
        }

        yield from self._iterative_compare(comparison)

    def save(self, _id, post, insert=True):
        """
        Save information to the database

        Parameters
        ----------
        _id : str
            ID of device

        post : dict
            Information to place in database

        insert : bool, optional
            Whether or not this a new device to the database

        Raises
        ------
        DuplicateError:
            If insert is True, but there is already a device with the provided
            _id

        SearchError:
            If insert is False, but there is no device with the provided _id

        PermissionError:
            If the write operation fails due to issues with permissions
        """
        with _load_and_store_context(self) as db:
            # New device
            if insert:
                if _id in db.keys():
                    raise DuplicateError(f"Device {_id} already exists")
                # Add _id keyword
                post.update({'_id': _id})
                # Add to database
                db[_id] = post
            # Updating device
            else:
                # Edit information
                try:
                    db[_id].update(post)
                except KeyError:
                    raise SearchError("No device found {}".format(_id))

    def delete(self, _id):
        """
        Delete a device instance from the database

        Parameters
        ----------
        _id : str
            ID of device

        Raises
        ------
        PermissionError:
            If the write operation fails due to issues with permissions
        """
        with _load_and_store_context(self) as db:
            try:
                db.pop(_id)
            except KeyError:
                raise SearchError(
                    f'ID not found in database: {_id!r}'
                ) from None
