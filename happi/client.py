import os
import sys
import math
import logging
import inspect
import time as ttime
import configparser

from . import containers
from .device import HappiItem, Device
from .errors import EntryError, DatabaseError, SearchError
from .backends import backend, _get_backend
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
        Mapping of HappiItem namees to class types

    Raises
    -----
    DatabaseError:
        Raised if the Client fails to instantiate the Database
    """
    # HappiItem information
    _client_attrs = ['_id', 'type', 'creation', 'last_edit']
    _id = 'name'
    # Store device types seen by client
    device_types = {'Device': Device,
                    'HappiItem': HappiItem}

    def __init__(self, database=None, **kwargs):
        # Get HappiItem Mapping
        self.device_types.update(dict([(name, cls) for (name, cls) in
                                       inspect.getmembers(containers,
                                                          inspect.isclass)
                                       if issubclass(cls, HappiItem)]))
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
        if len(kwargs) == 0:
            raise SearchError('No information pertinent to device given')
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
        device_cls : :class:`.HappiItem` or name of class
            The Device HappiItem to instantiate

        kwargs :
            Information to pass through to the device, upon initialization

        Returns
        -------
        device :
            An instantiated version of the device

        Raises
        ------
        TypeError:
            If the provided class is not a subclass of :class:`.HappiItem`


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
        # Check that this is a valid HappiItem
        if not issubclass(device_cls, HappiItem):
            raise TypeError('{!r} is not a subclass of '
                            'HappiItem'.format(device_cls))
        device = device_cls(**kwargs)
        # Add the method to the device
        device.save = lambda: self.add_device(device)
        return device

    def add_device(self, device):
        """
        Add a new device into the database

        Parameters
        ----------
        device : :class:`.HappiItem`
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
        logger.info('HappiItem %r has been succesfully added to the '
                    'database', device)

    def find_device(self, **post):
        """
        Used to query the database for an individual HappiItem

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
        device : :class:`.HappiItem`
            A device that matches the characteristics given
        """
        logger.debug("Gathering information about the device ...")
        doc = self.find_document(**post)
        # Instantiate HappiItem
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
                # HappiItem identification
                _id = post[self._id]
                logger.debug('Attempting to initialize %s...', _id)
                # Load HappiItem
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
            :class:`.HappiItem`

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
                    logger.error("HappiItem %s was missing attribute %s",
                                 dev.name, e)

    def remove_device(self, device):
        """
        Remove a device from the database

        Parameters
        ----------
        device : :class:`.HappiItem`
            HappiItem to be removed from the database
        """
        # HappiItem Check
        if not isinstance(device, HappiItem):
            raise ValueError("Must supply an object of type `HappiItem`")
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
        if not isinstance(device, HappiItem):
            raise ValueError('{!r} is not a subclass of '
                             'HappiItem'.format(device))
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
        logger.debug('HappiItem %r has been validated.', device)

    def _store(self, device, insert=False):
        """
        Store a document in the database

        Parameters
        ----------
        post : :class:`.HappiItem`
            HappiItem to save

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
                logger.debug("HappiItem %r defines an extra piece of "
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
            raise EntryError('HappiItem did not supply the proper information '
                             'to interface with the database, missing {}'
                             ''.format(self._id))
        # Store information
        logger.info('Adding / Modifying information for %s ...', _id)
        self.backend.save(_id, post, insert=insert)

    @classmethod
    def from_config(cls, cfg=None):
        """
        Create a client from a configuration file specification

        Configuration files looking something along the lines of:

        .. code::

            [DEFAULT]
            path=path/to/my/db.json

        All key value pairs will be passed directly into backend construction
        with the exception of the key ``backend`` which can be used to specify
        a specific type of backend if this differs from the configured default.

        Parameters
        ----------
        cfg: str, optional
            Path to a configuration file. If not entered, :meth:`.find_config`
            will be use.
        """
        # Find a configuration file
        if not cfg:
            cfg = cls.find_config()
        # Parse configuration file
        cfg_parser = configparser.ConfigParser()
        cfg_file = cfg_parser.read(cfg)
        logger.debug("Loading configuration file at %r", cfg_file)
        db_info = cfg_parser['DEFAULT']
        # If a backend is specified use it, otherwise default
        if 'backend' in db_info:
            db_str = db_info.pop('backend')
            db = _get_backend(db_str)
        else:
            db = backend
        logger.debug("Using Happi backend %r", db)
        # Create our database with provided kwargs
        return cls(database=db(**dict(db_info.items())))

    @staticmethod
    def find_config():
        """
        Search for a ``happi`` configuration file

        We first query the environment variable ``$HAPPI_CFG`` to see if this
        points to a specific configuration file. If this is not present, the
        variable set by ``$XDG_CONFIG_HOME`` or if  that is not set
        ``~/.config``

        Returns
        -------
        path: str
            Absolute path to configuration file

        Raises
        ------
        EnvironmentError:
            If no configuration file can be found by the methodology detailed
            above
        """
        # Point to with an environment variable
        if os.environ.get('HAPPI_CFG', False):
            happi_cfg = os.environ.get('HAPPI_CFG')
            logger.debug("Found $HAPPI_CFG specification for Client "
                         "configuration at %s", happi_cfg)
            return happi_cfg
        # Search in the current directory and home directory
        else:
            config_dir = (os.environ.get('XDG_CONFIG_HOME')
                          or os.path.expanduser('~/.config'))
            logger.debug('Searching for Happi config in %s', config_dir)
            for path in ('.happi.cfg', 'happi.cfg'):
                full_path = os.path.join(config_dir, path)
                if os.path.exists(full_path):
                    logger.debug("Found configuration file at %r", full_path)
                    return full_path
        # If found nothing
        raise EnvironmentError("No happi configuration file found. "
                               "Check HAPPI_CFG.")

    def choices_for_field(self, field):
        """
        List all choices for a given field

        Parameters
        ----------
        field : string
            search field to list all possible choices for
            i.e 'beamline', 'name', 'z', 'prefix', etc.

        Raises
        ------
        SearchError
            If no devices in the database have an entry for the given field

        Returns
        -------
        field_choices : list
            list of choices for a given field that are in the database
        """
        field_choices = set()
        for dev in self.all_devices:
            try:  # Want to ignore error if 'dev' doesn't have 'field'
                choice = getattr(dev, field)
                field_choices.add(choice)
            except AttributeError:
                pass
        if len(field_choices) == 0:
            raise SearchError('No entries found with given field')
        return field_choices
