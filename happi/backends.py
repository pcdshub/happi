"""
Abstract backend database options
"""
############
# Standard #
############
import abc
import fcntl
import os.path
import logging

###############
# Third Party #
###############
import simplejson as json
from six import with_metaclass
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure


##########
# Module #
##########
from .errors import DatabaseError, SearchError, DuplicateError

logger = logging.getLogger(__name__)


class Backend(abc.ABCMeta):
    """
    Abstract interface for backend database
    """
    @abc.abstractproperty
    def devices(self):
        """
        List of all device sub-dictionaries
        """
        raise NotImplementedError


    @abc.abstractmethod
    def find(self, multiples=False, **kwargs):
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
        raise NotImplementedError


    @abc.abstractmethod
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
        raise NotImplementedError


    @abc.abstractmethod
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
        raise NotImplementedError



class MongoBackend(with_metaclass(Backend)):
    """
    Abstraction for MongoDB backend

    Parameters
    ----------
    host : str, optional
        Hostname for MongoDB

    user : str, optional
        Username for MongoDB instance

    pw :str, optional
        Password for given username

    host : str, optional
        Host of the MongoDB instance

    db : str, optional
        Database name within the MongoDB instance

    timeout : float, optional
        Time to wait for connection attempt
    """
    _timeout  = 5
    _conn_str = 'mongodb://{user}:{pw}@{host}/{db}' #String for login

    def __init__(self, host=None, user=None,
                 pw=None, db=None, timeout=None):
        #Default timeout
        timeout = timeout or self._timeout
        #Format connection string
        conn_str     = self._conn_str.format(user=user,pw=pw,host=host,db=db)

        logging.debug('Attempting connection using {} '.format(conn_str))
        self._client = MongoClient(conn_str, serverSelectionTimeoutMS=timeout)
        self._db     = self._client[db] 

        #Load collection
        try:
            if self._coll_name not in self._db.collection_names():
                raise DatabaseError('Unable to locate collection {} '
                                    'in database'.format(self._coll_name))

            self._collection = self._db[self._coll_name]

        #Unable to view collection names
        except OperationFailure as e:
            raise PermissionError(e)

        #Unable to connect to MongoDB instance
        except ServerSelectionTimeoutError:
            raise DatabaseError('Unable to connect to MongoDB instance, check '
                                'that the server is running on the host and port '
                                'specified at startup')


    @property
    def all_devices(self):
        """
        List of all device sub-dictionaries
        """
        return self._collection.find()


    def find(self, multiples=False, **kwargs):
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
        #Find all matches
        cur = list(self._collection.find(kwargs))
        #Only return a single device if requested
        if not multiples:
            #Grab first item
            try:
                cur = cur[0]
            #If no items were returned
            except IndexError:
                logger.debug("No items found when searching for multiples")
        return cur


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
        try:
            #Add to database
            result = self._collection.update_one({'_id'  : _id},
                                                 {'$set' : post},
                                                 upsert = insert)
        except OperationFailure:
            raise PermissionError("Unauthorized command, make sure you are "
                                  "using a user with write permissions")

        if insert and not result.upserted_id:
            raise DuplicateError('Device with id {} has already been entered into '
                                 'the database, use load_device and save if you wish to make '
                                 'changes to the device'.format(_id))

        if not insert and result.matched_count == 0:
            raise SearchError('No device found with id {} please, if this is a '
                              'new device, try add_device. If not, make '
                              'sure that the device information being sent is '
                              'correct'.format(_id))


    def delete(self, _id):
        """
        Delete a device instance from the database

        Parameters
        ----------
        _id : str
            ID of device
        """
        self._collection.delete_one({'_id': _id})


class JSONBackend(with_metaclass(Backend)):
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
        self.path  = path

        #Create a new JSON file if requested
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
        #Do not overwrite existing databases
        if os.path.exists(self.path):
            raise PermissionError("File {} already exists. Can not initialize "
                                  "a new database.".format(self.path))
        #Dump an empty dictionary
        json.dump({}, open(self.path, "w+"))


    def load(self):
        """
        Load the JSON database

        """
        #Create file handle
        handle = open(self.path, 'r')
        return json.load(handle)


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
        #Create file handle
        handle = open(self.path, 'w+')
        #Create lock in filesystem
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        #Dump to file
        try:
            json.dump(db, handle, sort_keys=True, indent=4)

        finally:
            #Release lock in filesystem
            fcntl.flock(handle, fcntl.LOCK_UN)

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
        #Load database
        db = self.load()

        #Search by _id, separated for speed
        if _id:
            try:
                matches = [db[_id]]
            except KeyError:
                matches = []

        #Find devices matching kwargs
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
        #Load database
        db = self.load()

        #New device
        if insert:
            if _id in db.keys():
                raise DuplicateError("Device {} already exists".format(_id))
            #Add _id keyword
            post.update({'_id' : _id})
            #Add to database
            db[_id] = post

        #Updating device
        else:
            #Edit information
            try:
                db[_id].update(post)
            except KeyError:
                raise SearchError("No device found {}".format(_id))

        #Save changes
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
        #Load database
        db = self.load()
        #Remove device
        try:
            db.pop(_id)
        except KeyError:
            logger.warning("Device {} not found in database".format(_id))
        #Store database
        self.store(db)


