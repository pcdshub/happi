import sys
import math
import logging
import inspect
import time as ttime

from . import containers
from .device import Device
from .errors import EntryError, DatabaseError, SearchError
from .backends import backend
from .loader import from_container

logger = logging.getLogger(__name__)


class Client:
    """
    The client to control the contents of the Happi Database

    Parameters
    ----------
    database : happi.backends.Backend
        A already instantiated backend

    kwargs:
        Passed to the `db_type` backend

    Attributes
    ----------
    device_types : dict
        Mapping of Container namees to class types

    Raises
    -----
    DatabaseError:
        Raised if the Client fails to instantiate the Database
    """
    # Device information
    _client_attrs = ['_id', 'type', 'creation', 'last_edit']
    _id = 'prefix'
    # Store device types seen by client
    device_types = {'Device': Device}

    def __init__(self, database=None, **kwargs):
        # Get Container Mapping
        self.device_types.update(dict([(name, cls) for (name, cls) in
                                       inspect.getmembers(containers,
                                                          inspect.isclass)
                                       if issubclass(cls, Device)]))
        # Use supplied backend
        if database:
            self.backend = database
        # Load database
        else:
            logger.debug("No database given, using '%s'", backend)
            try:
                self.backend = backend(**kwargs)
            except Exception as exc:
                raise DatabaseError("Failed to instantiate "
                                    "a {} backend".format(backend)) from exc

    def find_document(self, **kwargs):
        """
        Load a device document from the database

        If multiple matches are found, a single document will be returned to
        the user. How the database will choose to select this device is based
        on each individual implementation

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
        # Request information from backend
        post = self.backend.find(multiples=False, **kwargs)
        # Check result, if not found let the user know
        if not post:
            raise SearchError('No device information found that '
                              'matches the search criteria')
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
        TypeError:
            If the provided class is not a subclass of :class:`.Device`


        Example
        -------
        .. code::

            device = client.create_device(Device,   name='my_device' ...)
            device = client.create_device('Device', name='my_device',...)

        See Also
        --------
        :attr:`.device_types`
        """
        # If specified by a string
        if device_cls in self.device_types:
            device_cls = self.device_types[device_cls]
        # Check that this is a valid Container
        if not issubclass(device_cls, Device):
            raise TypeError('{!r} is not a subclass of '
                            'Device'.format(device_cls))
        device = device_cls(**kwargs)
        # Add the method to the device
        device.save = lambda: self.add_device(device)
        return device

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
        logger.info("Storing device %r ...", device)
        # Store post
        self._store(device, insert=True)
        # Log success
        logger.info('Device %r has been succesfully added to the '
                    'database', device)

    def find_device(self, **post):
        """
        Used to query the database for an individual Device

        If multiple devices are found, only the first is returned

        Parameters
        ----------
        post :
            Information to pertinent to the device

        Raises
        ------
        SearchError
            If no match for the given information is found

        Returns
        -------
        device : :class:`.Device`
            A device that matches the characteristics given
        """
        logger.debug("Gathering information about the device ...")
        doc = self.find_document(**post)
        # Instantiate Device
        logger.debug("Instantiating device based on found information ...")
        try:
            device = self.create_device(doc['type'], **doc)
        except (KeyError, TypeError) as exc:
            raise EntryError('The information relating to the device class '
                             'has been modified to the point where the object '
                             'can not be initialized, please load the '
                             'corresponding document') from exc

        # Add the save method to the device
        device.save = lambda: self._store(device, insert=False)
        return device

    def load_device(self, use_cache=True, **post):
        """
        Find a device in the database and instantiate it

        Essentially a shortcut for:

        .. code:: python

            container = client.find_device(name='...')
            device = from_container(container)

        Parameters
        ----------
        post:
            Passed to :meth:`.Client.find_device`

        use_cache: bool, optional
            Choice to use a cached device. See :meth:`.from_container` for more
            information

        Returns
        -------
        obj:
            Instantiated object
        """
        cntr = self.find_device(**post)
        return from_container(cntr, use_cache=use_cache)

    def validate(self):
        """
        Validate all of the devices in the database by attempting to initialize
        them and asserting their mandatory information is present. Information
        is written to the logger

        Returns
        -------
        ids : list
            List of device ids that have failed verification
        """
        bad = list()
        logger.debug('Loading database to validate contained devices ...')
        for post in self.backend.all_devices:
            # Try and load device based on database info
            try:
                # Device identification
                _id = post[self._id]
                logger.debug('Attempting to initialize %s...', _id)
                # Load Device
                device = self.find_device(**post)
                logger.debug('Attempting to validate ...')
                self._validate_device(device)
            except KeyError:
                logger.error("Post has no id  %s", post)
            # Log all generated exceptions
            except Exception as e:
                logger.warning("Failed to validate %s because %s", _id, e)
                bad.append(_id)
            # Report successes
            else:
                logger.debug('Successfully validated %s', _id)
        return bad

    @property
    def all_devices(self):
        """
        A list of all contained devices
        """
        return self.search()

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
        .. code::

            gate_valves = client.search(type='Valve')
            hxr_valves  = client.search(type='Valve', beamline='HXR')
        """
        try:
            cur = self.backend.find(multiples=True, **kwargs)
        except TypeError:
            return None
        # If beamline position matters
        if start or end:
            if not end:
                end = math.inf
            if start >= end:
                raise ValueError("Invalid beamline range")
            # Find all values within range
            cur = [info for info in cur
                   if start <= info['z'] and info['z'] < end]
        if not cur:
            return None
        elif as_dict:
            return cur
        else:
            return [self.find_device(**info) for info in cur]

    def export(self, path=sys.stdout, sep='\t', attrs=None):
        """
        Export the contents of the database into a text file

        Parameters
        ----------
        path : File Handle
            File-like object to save text file

        sep : str
            Separator to place inbetween columns of information

        attrs : iterable
            Attributes to include, these will be a list of values
        """
        # Load documents
        devs = self.all_devices
        logger.info('Creating file at %s ...', path)
        # Load device information
        with path as f:
            for dev in devs:
                try:
                    f.write(sep.join([getattr(dev, attr)
                                      for attr in attrs])
                            + '\n')
                except KeyError as e:
                    logger.error("Device %s was missing attribute %s",
                                 dev.name, e)

    def remove_device(self, device):
        """
        Remove a device from the database

        Parameters
        ----------
        device : :class:`.Device`
            Device to be removed from the database
        """
        # Device Check
        if not isinstance(device, Device):
            raise ValueError("Must supply an object of type `Device`")
        logger.info("Attempting to remove %r from the "
                    "collection ...", device)
        # Check that device is in the database
        try:
            _id = getattr(device, self._id)
            self.find_document(_id=_id)
        # Log and re-raise
        except SearchError:
            logger.exception('Target device was not found in the database')
            raise
        else:
            self.backend.delete(_id)

    def _validate_device(self, device):
        """
        Validate that a device has all of the mandatory information
        """
        logger.debug('Validating device %r ...', device)

        # Check type
        if not isinstance(device, Device):
            raise ValueError('{!r} is not a subclass of '
                             'Device'.format(device))
        logger.debug('Checking mandatory information has been entered ...')
        # Check that all mandatory info has been entered
        missing = [info.key for info in device.entry_info
                   if not info.optional and
                   info.default == getattr(device, info.key)]
        # Abort initialization if missing mandatory info
        if missing:
            raise EntryError('Missing mandatory information ({}) for {}'
                             ''.format(', '.join(missing),
                                       device.__class__.__name__))
        logger.debug('Device %r has been validated.', device)

    def _store(self, device, insert=False):
        """
        Store a document in the database

        Parameters
        ----------
        post : :class:`.Device`
            Device to save

        insert : bool, optional
            Set to True if this is a new entry

        Raises
        ------
        DuplicateError:
            When _id already exists

        EntryError:
            If the device doesn't the correct information

        Todo
        ----
        Enforce parent is an already entered name
        """
        logger.debug('Loading a device into the collection ...')

        # Validate device is ready for storage
        self._validate_device(device)
        # Grab information from device
        post = device.post()
        # Store creation time
        creation = post.get('creation', ttime.ctime())
        # Clean supplied information
        [post.pop(key) for key in self._client_attrs if key in post]
        # Note that device has some unrecognized metadata
        for key in post.keys():
            if key not in device.info_names:
                logger.debug("Device %r defines an extra piece of "
                             "information under the keyword %s",
                             device, key)
        # Add metadata from the Client Side
        post.update({'type': device.__class__.__name__,
                     'creation': creation,
                     'last_edit': ttime.ctime()})
        # Find id
        try:
            _id = post[self._id]
        except KeyError:
            raise EntryError('Device did not supply the proper information to '
                             'interface with the database, missing {}'
                             ''.format(self._id))
        # Store information
        logger.info('Adding / Modifying information for %s ...', _id)
        self.backend.save(_id, post, insert=insert)
