"""
MongoDB Backend Implementation using the ``PyMongo`` package.
"""
import logging
import re

import bson.regex
from pymongo import MongoClient
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError

from ..errors import DatabaseError, DuplicateError, SearchError
from .core import _Backend

logger = logging.getLogger(__name__)


class MongoBackend(_Backend):
    """
    Abstraction for MongoDB backend.

    Parameters
    ----------
    host : str, optional
        Hostname for MongoDB.
    user : str, optional
        Username for MongoDB instance.
    pw : str, optional
        Password for given username.
    host : str, optional
        Host of the MongoDB instance.
    db : str, optional
        Database name within the MongoDB instance.
    timeout : float, optional
        Time to wait for connection attempt.
    cfg_path : str, optional
        Path to the happi config.
    """

    _timeout = 5
    _conn_str = 'mongodb://{user}:{pw}@{host}/{db}'  # String for login

    def __init__(self, host=None, user=None,
                 pw=None, db=None, collection=None,
                 timeout=None, cfg_path=None):
        # Default timeout
        timeout = timeout or self._timeout
        # Format connection string
        conn_str = self._conn_str.format(user=user, pw=pw,
                                         host=host, db=db)
        logging.debug('Attempting connection using %s ', conn_str)
        self._client = MongoClient(conn_str, serverSelectionTimeoutMS=timeout)
        self._db = self._client[db]
        # Load collection
        try:
            if collection not in self._db.list_collection_names():
                raise DatabaseError('Unable to locate collection {} '
                                    'in database'.format(collection))
            self._collection = self._db[collection]
        # Unable to view collection names
        except OperationFailure as e:
            raise PermissionError(e)
        # Unable to connect to MongoDB instance
        except ServerSelectionTimeoutError:
            raise DatabaseError('Unable to connect to MongoDB instance, check '
                                'that the server is running on the host and '
                                'port specified at startup')

    @property
    def all_items(self):
        """List of all item sub-dictionaries."""
        return self._collection.find()

    def find(self, to_match):
        """
        Yield all instances that match the given search criteria.

        Parameters
        ----------
        to_match : dict
            Requested information.
        """

        yield from self._collection.find(to_match)

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

        if key in to_match:
            raise ValueError('Cannot specify the same key in `to_match` as '
                             'the key for the range.')

        match = {key: {'$gte': start}}
        if stop is not None:
            if start >= stop:
                raise ValueError(f"Invalid range: {start} >= {stop}")
            match[key]['$lt'] = stop

        match.update(**to_match)
        yield from self._collection.find(match)

    def get_by_id(self, _id):
        """
        Get an item by ID if it exists, or return None.

        Parameters
        ----------
        _id : str
            The item ID.
        """

        for item in self._collection.find({'_id': _id}):
            return item

    def find_regex(self, to_match, *, flags=re.IGNORECASE):
        """
        Yield all instances that match the given search criteria.

        Parameters
        ----------
        to_match : dict
            Requested information, with each value being a regular expression.
        """

        regexes = {}
        for key, value in to_match.items():
            try:
                reg = re.compile(value, flags=flags)
                regexes[key] = bson.regex.Regex.from_native(reg)
            except Exception as ex:
                raise ValueError(f'Failed to create regular expression from '
                                 f'{key}={value!r}: {ex}') from ex

        yield from self._collection.find(regexes)

    def save(self, _id, post, insert=True):
        """
        Save information to the database.

        Parameters
        ----------
        _id : str
            ID of item.
        post : dict
            Information to place in database.
        insert : bool, optional
            Whether or not this a new item to the database.

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

        try:
            # Add to database
            result = self._collection.update_one({'_id': _id},
                                                 {'$set': post},
                                                 upsert=insert)
        except OperationFailure:
            raise PermissionError(
                "Unauthorized command, make sure you are "
                "using a user with write permissions"
            )

        if insert and not result.upserted_id:
            raise DuplicateError(
                "Item with id {} has already been entered "
                "into the database, use load_item and "
                "save if you wish to make changes to the "
                "item".format(_id)
            )

        if not insert and result.matched_count == 0:
            raise SearchError(
                "No item found with id {} please, if this is "
                "a new item, try add_item. If not, make "
                "sure that the item information being sent is "
                "correct".format(_id)
            )

    def delete(self, _id):
        """
        Delete an item instance from the database.

        Parameters
        ----------
        _id : str
            ID of item.
        """

        res = self._collection.delete_one({'_id': _id})
        if res.deleted_count < 1:
            raise SearchError(f'ID not found in database: {_id!r}')
