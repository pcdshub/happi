#####################
# Standard Packages #
#####################
import logging
import inspect
import numpy as np #Could be removed if necessary
import time  as ttime
from pymongo import MongoClient
from pymongo.errors import OpertaionFailure, DuplicateKeyError

###################
# Module Packages #
###################
import .device
import .containers
from .device import Device
from .utils  import PermissionError, SearchError, DuplicateError

logger = logging.getLogger(__name__)

class Client:
    """
    The client to control the contents of the Happi Database
    
    Parameters
    ----------
    user : str, optional
        Username for MongoDB instance

    pw :str, optional
        Password for given username

    host : str, optional
        Host of the MongoDB instance

    timeout : float, optional
        Time to wait for connection attempt
    """
    #MongoDB information
    self._host       = 'psdev03' #Hostname of MongoDB instance
    self._port       = None      #Port of MongoDB instance
    self._user       = 'happi'   #Username
    self._pw         = 'happi'   #Password
    self._conn_str   = 'mongodb://{user}:{pw}@{host}{db}' #String for login
    self._id         = 'base'             #Attribute name to use as unique id
    self._db_name    = 'test_db'          #MongoDB name
    self._coll_name  = 'test_collection'  #Relevant Collection name
    self._timeout    = 5                  #Connection timeout

    #Device information
    self._client_attrs = ['_id', 'type', 'creation', 'last_edit']
    self._fixed_attrs  = ['base', 'alias']
    self.device_types  = {'Device' : Device}

    def __init__(self, host=None, port=None, user=None, pw=None, timeout=None):
        #Load database
        conn_str     = self._conn_str.format(**kwargs)
        self._client = MongoClient(conn_str, connectTimeoutMS=self._timeout)
        self._db     = client[self._db] 

        #Load collection
        try:
            if self._coll_name not in self._db.collection_names():
                raise DatabaseError('Unable to locate collection {} '
                                    'in database'.format(self._collection))

        except OperationFailure, e:
            raise PermissionError(e)

        self._collection = self._db[self._collection]

        #Get Container Mapping
        self.device_types.update(dict([(name,cls) for (name,cls) in
                                       inspect.getmembers(containers,inspect.isclass)
                                       if issubclass(cls,Device)
                                ]))


    def find_document(self, **kwargs):
        """
        Load a device document from the MongoDB

        If multiple devices are found, only the first is returned. Order is
        based on the natural order inside the MongoDB instance

        Parameters
        ----------
        kwargs :
            Add information to locate the device in keyword pairs

        Returns
        -------
        document : dict
            A dict that matches the specified information.

        Raises
        ------
        SearchError:
            If no document with the given information is found

        See Also
        --------
        :meth:`.find_device`, :meth:`.search`
        """
        #Separated for increased speed
        if self._id in kwargs:
            post = self._collection.find_one({'_id': kwargs[self._id]})

        else:
            post = self._collection.find_one(kwargs)

        #Check result, if not found let the user know
        if not post:
            raise SearchError('No device information found that '
                              'matches the seach criteria')
        return post


    def create_device(self, device_cls, **kwargs):
        """
        Create a new device

        Parameters
        ----------
        device_cls : :class:`.Device` or name of class
            The Device Container to instantiate

        kwargs :
            Information to pass through to the device, upon initialization

        Returns
        -------
        device :
            An instantiated version of the device

        Raises
        ------
        ValueError:
            If the provided class is not a subclass of :class:`.Device`

        See Also
        --------
        :attr:`.device_types`
        """
        #If specified by a string
        if device_cls in self.device_types:
            device_cls = self.device_types[device_cls]


        #Check that this is a valid Container
        if not issubclass(device_cls, Device):
            raise ValueError('{!r} is not a subclass of '
                             'Device'.format(device_cls))

        return device_cls(**kwargs)


    def add_device(self, device):
        """
        Add a new device into the database

        Parameters
        ----------
        device : :class:`.Device`
            The device to store in the database

        Raises
        ------
        EntryError:
            If all of the mandatory information for the device has not been
            specified or there is already a device with that ``id`` in the 
            database
        """
        logger.info("Storing device {!r} ...".format(device))

        #Validate device is ready for storage
        self._validate_device(device)

        #Grab information from device
        post = device.post()

        #Clean supplied information
        [post.pop(key) for key in self._client_attrs if key in post]

        #Note that device has some unrecognized metadata
        if device.extraneous:
            for key in device.extraneous.keys():
                logger.info("Device {!r} defines an extra piece of information "
                            "under the keyword {}".format(device, key))


        #Add metadata from the Client Side
        post.update({'type'     : device.__class__.__name__})
                    'creation'  : ttime.ctime(),
                    })

        #Store post
        self._store(post)

        #Log success
        logger.info({'Device {!r} has been succesfully added to the '
                     'database'.format(device))


    def load_device(self, **post):
        """
        Used to query the database for an individual Device

        If multiple devices are found, only the first is returned

        Parameters
        ----------
        post :
            Information to pertinent to the device 

        Returns
        -------
        device : :class:`.Device` or None
            A device that matches the characteristics given
        """
        logger.debug("Gathering information about the device ...")
        doc = self.find_document(**post)

        #Instantiate Device
        logger.debug("Instantiating device based on found information ...")
        try:
            device = self.create_device(post['type'], **post)

        except KeyError, ValueError:
            raise EntryError('The information relating to the device class has '
                             'been modified to the point where the object can not '
                             'be initialized, please load the corresponding '
                             'document')

        #Record the fixed attributes
        logger.debug("Creating save method for device ...")
        fixed = dict([(attr, getattr(device, attr))
                      for attr in self._fixed_attrs])

        #Create the save method
        def save():
            #Check if a fixed attribute has been changed
            diff = [attr for key,value in fixed.items()
                    if current[key] != getattr(device,key)]

            #Raise an error if changed
            if diff:
                raise EntryError('Fixed entries {} have been modfied, this '
                                 'should be entered as a new device.')
                                 ''.format(', '.join(diff))

            #Check that all mandatory information is filled
            self._validate_device(device)

            #Return the storage function
            return self._store(device.post(), insert=False)

        #Add the method to the device
        device.save = save

        return device


    def validate(self):
       """
        Validate all of the devices in the database by attempting to initialize
        them and asserting their mandatory information is present. Information
        is written to the logger

        Returns
        -------
        ids : list
            List of device ids that have failed verification

        Todo
        ----
        Automated script to scan database and alert invalid devices. Either
        send email or post to eLog to keep a running log of incorrect changes
        """
        bad = list()

        logger.debug('Loading database to validate contained devices ...')
        for post in self._collection.find():
            #Device identification
            _id = post['id']
            logger.info('Attempting to validate {} ...'.format(_id))

            #Try and load device based on database info
            try:
                logger.debug('Attempting to initialize ...') 
                device = self.load_device(**post)
                logger.debug('Attempting to validate ...')
                self._validate_device(device)

            #Log all generated exceptions
            except Exception:
                logger.exception("Failed to validate {}".format(_id))
                bad.append(_id)

            #Report successes
            else:
                logger.debug('Successfully validated {}'.format(_id))

        return bad


    def search(self, start=0., end=None, as_dict=False, **kwargs):
        """
        Search the database for a device or devices
        
        Parameters
        -----------
        as_dict : bool, optional
            Return the information as a list of dictionaries or a list of
            :class:`.Device` containers

        start : float, optional
            Minimum beamline position to include devices

        end : float, optional
            Maximum beamline position to include devices

        kwargs :
            Information to filter through the database structured as key, value
            pairs for the desired pieces of EntryInfo

        Returns
        -------
        Either a list of devices or dictionaries

        Example
        -------
        gate_valves = client.search(type='Valve')
        hxr_valves  = client.search(type='Valve', beamline='HXR')

        Todo
        ----
        Search on regular expression
        """
        try:
            cur = list(self._collection.find(kwargs))

        except TypeError:
            return None

        #If beamline position matters
        if start or end:

            #Define range 
            def in_range(val):
                if not end:
                    end = np.inf
                    
                return start <=  val < end

            cur = [info for info in cur if in_range(info['z'])

        if as_dict:
            return cur

        else:
            return [Device(info) for info in cur]
       
        

    def export(self, path=None, sep='\t', attrs=None):
        """
        Export the contents of the database into a text file

        Parameters
        ----------
        path : str
            Filepath to save text file

        sep : str
            Separator to place inbetween columns of information

        attrs : iterable
            Attributes to include, these will be a list of values
        """
        #Load documents
        docs = list(self._collection.find())
        
        logger.info('Creating file at {} ...'.format(path))

        #Load device information
        with open(path,'w+') as f:
            for post in docs:
                try:
                    f.write(sep.join([post[attr] for attr in attrs]))

                except KeyError as e:
                    logger.error("Device {} was missing "
                                 "attribute {}".format(post['_id'],
                                                       e))

    def remove_device(self, device):
        """
        Remove a device from the database

        Parameters
        ----------
        device : :class:`.Device`
            Device to be removed from the database
        """
        #Device Check
        if not isinstance(device, Device):
            raise ValueError("Must supply an object of type `Device`")
 
        logger.info("Attempting to remove {!r} from the "
                    "collection ...".format(device))

        #Check that device is in the database
        try:
            info = device.post()
            self.find_document(**info)

        except SearchError:
            logger.exception(e)
            raise

        else:
            #Deleted
            cursor = self._collection.delete_one({'_id':post.pop(self._id)})

            if cursor.deleted_count :
                logging.info("{} succesfully deleted from database"})


    def _validate_device(self, device):
        """
        Validate that a device is an instance of :class:`.Device` and has all
        of the mandatory information
        """
        logger.debug('Validating device {!r} ...'.format(device))

        #Check type
        if not isinstance(device, Device):
            raise ValueError('{!r} is not a subclass of '
                             'Device'.format(device))

        logger.debug('Checking mandatory information has been entered ...')

        #Check that all mandatory info has been entered
        missing = [info for info in device.mandatory_info
                   if device.default == getattr(device, info)]

        #Abort initialization if missing mandatory info
        if missing:
            raise EntryError('Missing mandatory information ({}) for {}' 
                             ''.format(', '.join(missing), device.__class__.__name__))

        logger.debug('Device {!r} has been validated.'.format(device))



    def _store(self, post, insert=False):
        """
        Store a document in the database
        
        Parameters
        ----------
        post : dict
            Information to place in the databse

        insert : bool, optional
            Set to True if this is a new entry

        Raises
        ------
        DuplicateError:
            When _id already exists

        EntryError:
            If the device doesn't 
        """
        logger.debug('Loading a post into the collection ...') 
        try:
            #Add some metadata
            _id = post[self._id]

            logger.info('Adding / Modifying information for {} ...'.format(_id))

            post.update({'last_edit' : ttime.ctime()})

            #Add to database
            result = self._collection.update_one({'_id'  : _id},
                                                 {'$set' : post},
                                                 upsert = insert)

        except KeyError:
            raise EntryError('Device did not supply the proper information to '
                             'interface with the database')

        except OperationFailure:
            raise PermissionError("Unauthorized command, make sure you are "
                                  "using a user with write permissions")

        logger.info('{} documents have been modified ...'
                     ''.format(result.matched_count))

        if insert and not result.upserted_id:
            raise DuplicateError('Device with id {} has already been entered into '
                                 'the database, use load_device and save if you wish to make '
                                 'changes to the device'.format(_id))

        if not insert and result.matched_count == 0:
            raise SearchError('No device found with id {} please, if this is a '
                              'new device, set insert to True. If not, make '
                              'sure that the device information being sent is '
                              'correct'.format(_id))

