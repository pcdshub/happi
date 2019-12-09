"""
Backend implemenation using simplejson
"""
import os
import os.path
import logging

import simplejson as json

from .core import Backend
from ..errors import SearchError, DuplicateError

logger = logging.getLogger(__name__)


try:
    import fcntl
except ImportError:
    logger.warning("Unable to import 'fcntl'. Will be unable to lock files")
    fcntl = None


class JSONBackend(metaclass=Backend):
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

    @property
    def all_devices(self):
        """
        All of the devices in the database
        """
        return list(self.load().values())

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
        with open(self.path, "w+") as f:
            json.dump({}, f)

    def load(self):
        """
        Load the JSON database
        """
        with open(self.path, 'r') as f:
            return json.load(f)

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

    def find(self, _id=None, multiples=False, **kwargs):
        """
        Find an instance or instances that matches the search criteria

        Parameters
        ----------
        multiples : bool
            Find a single result or all results matching the provided
            information

        kwargs :
            Requested information
        """
        # Load database
        db = self.load()

        # Search by _id, separated for speed
        if _id:
            try:
                matches = [db[_id]]
            except KeyError:
                matches = []

        # Find devices matching kwargs
        else:
            matches = [doc for doc in db.values()
                       if all([value == doc[key]
                               for key, value in kwargs.items()])]

        if not multiples:
            try:
                matches = matches[0]
            except IndexError:
                matches = []

        return matches

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
        # Load database
        db = self.load()
        # New device
        if insert:
            if _id in db.keys():
                raise DuplicateError("Device {} already exists".format(_id))
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
        # Save changes
        self.store(db)

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
        # Load database
        db = self.load()
        # Remove device
        try:
            db.pop(_id)
        except KeyError:
            logger.warning("Device %s not found in database", _id)
        # Store database
        self.store(db)
