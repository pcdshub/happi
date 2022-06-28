import collections.abc
import configparser
import contextlib
import copy
import inspect
import itertools
import logging
import os
import re
import sys
import time as ttime
from typing import Any, Dict, List, Optional, Sequence, Type

from . import containers
from .backends import BACKENDS, DEFAULT_BACKEND
from .backends.core import _Backend
from .errors import DatabaseError, EntryError, SearchError, TransferError
from .item import HappiItem
from .loader import from_container
from .utils import deprecated

logger = logging.getLogger(__name__)


def _looks_like_database(obj):
    """Returns True if obj is a `Backend` or has certain Backend attributes."""
    return (isinstance(obj, _Backend) or
            all(
                hasattr(obj, attr) for attr in (
                    'find', 'all_devices', 'delete', 'save')
                )
            )


class SearchResult(collections.abc.Mapping):
    """
    A single search result from `Client.search`.

    Examples
    --------
    This result can be keyed for metadata as in:
    >>> result['name']

    The HappiItem can be readily retrieved:
    >>> result.item

    Or the object may be instantiated:
    >>> result.get()

    Attributes
    ----------
    item : happi.HappiItem
        The resulting container.
    metadata : dict
        The resulting HappiItem metadata.
    """

    def __init__(self, client, item):
        self._item = item
        self._instantiated = None
        self.client = client
        self.metadata = item.post()

    @property
    @deprecated("Use .item")
    def device(self):
        return self.item

    @property
    def item(self):
        if self._item is None:
            self._item = self.client.find_item(**self.metadata)
        return self._item

    def get(self, attach_md=True, use_cache=True, threaded=False):
        '''(get) ''' + from_container.__doc__
        if self._instantiated is None:
            self._instantiated = from_container(
                self.item, attach_md=attach_md, use_cache=use_cache,
                threaded=threaded
            )
        return self._instantiated

    def __getitem__(self, item):
        return self.metadata[item]

    def __iter__(self):
        yield from self.metadata

    def __len__(self):
        return len(self.metadata)

    def __repr__(self):
        return (
            f'{self.__class__.__name__}(client={self.client}, '
            f'metadata={self.metadata})'
        )

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, self.__class__):
            return ((self.client.backend == __o.client.backend)
                    and (self['_id'] == __o['_id']))
        else:
            return False

    def __hash__(self) -> int:
        return hash((self.client.backend, self['_id']))


class Client(collections.abc.Mapping):
    """
    The client to control the contents of the Happi Database.

    Parameters
    ----------
    database : happi.backends.Backend
        A already-instantiated backend.
    kwargs
        Keyword arguments passed to the ``database`` backend.

    Raises
    -----
    DatabaseError
        Raised if the Client fails to instantiate the Database.
    """

    # HappiItem information
    _client_attrs = ['_id', 'type', 'creation', 'last_edit']
    _id_key = 'name'
    _results_wrap_class = SearchResult

    def __init__(self, database=None, **kwargs):
        self._retain_cache = False

        # Use supplied backend
        if database:
            self.backend = database
            if not _looks_like_database(database):
                raise ValueError(f'{database!r} does not look like a database;'
                                 f' expecting an instantiated happi backend')
        # Load database
        else:
            logger.debug("No database given, using '%s'", DEFAULT_BACKEND)
            try:
                self.backend = DEFAULT_BACKEND(**kwargs)
            except Exception as exc:
                raise DatabaseError(
                    f"Failed to instantiate a {DEFAULT_BACKEND} backend"
                ) from exc

    @contextlib.contextmanager
    def retain_cache_context(self, clear_first: bool = True):
        """
        Context manager which can be used to retain the happi backend cache.

        Parameters
        ----------
        clear_first : bool, optional
            Clear the cache before entering the block.  Defaults to True.
        """
        if clear_first:
            self.backend.clear_cache()

        try:
            self._retain_cache = True
            yield
        finally:
            self._retain_cache = False

    def find_document(self, **kwargs):
        """
        Load an item document from the database.

        If multiple matches are found, a single document will be returned to
        the user. How the database will choose to select this item is based
        on each individual implementation

        Parameters
        ----------
        kwargs
            Keyword pairs of information used to locate the item

        Returns
        -------
        document : dict
            A dict that matches the specified information.

        Raises
        ------
        SearchError
            If no document with the given information is found.

        See Also
        --------
        :meth:`.find_item`, :meth:`.search`
        """

        if len(kwargs) == 0:
            raise SearchError("No information pertinent to item given")

        self._maybe_clear_cache()
        matches = list(itertools.islice(self.backend.find(kwargs), 1))
        if not matches:
            raise SearchError(
                "No item information found that matches the search criteria"
            )
        return copy.deepcopy(matches[0])

    def create_item(self, item_cls, **kwargs):
        """
        Instantiate a HappiItem from its container class and keyword arguments.

        Parameters
        ----------
        item_cls : type
            The HappiItem container class to instantiate.

        **kwargs :
            Information to pass through to the item, upon initialization.

        Returns
        -------
        item : object
            An instantiated version of the item.

        Raises
        ------
        TypeError
            If the provided class is not a subclass of :class:`.HappiItem`.

        Example
        -------
        .. code::

            item = client.create_item(Item, name='my_item' ...)
            item = client.create_item('Item', name='my_item',...)
        """

        # string -> class, if in the registry
        if item_cls in containers.registry:
            item_cls = containers.registry[item_cls]

        # Check that this is a valid HappiItem
        if isinstance(item_cls, str):
            raise TypeError(
                f'The container class {item_cls!r} is not in the registry'
            )

        if not (inspect.isclass(item_cls) and issubclass(item_cls, HappiItem)):
            raise TypeError(f"{item_cls!r} is not a subclass of HappiItem")

        item = item_cls(**kwargs)

        def save_item():
            self.add_item(item)

        # Add the method to the item
        item.save = save_item
        return item

    @deprecated("use .create_item")
    def create_device(self, device_cls, **kwargs):
        return self.create_item(device_cls, **kwargs)

    def add_item(self, item):
        """
        Add an item into the database.

        Parameters
        ----------
        item : :class:`.HappiItem`
            The item to store in the database.

        Returns
        -------
        _id : str
            The id of the item added.

        Raises
        ------
        EntryError
            If all of the mandatory information for the item has not been
            specified or there is already an item with that ``id`` in the
            database.
        """

        logger.info("Storing item %r ...", item)
        _id = self._store(item, insert=True)
        logger.info(
            "HappiItem %r has been succesfully added to the database",
            item
        )

        def save_item():
            self._store(item, insert=False)

        item.save = save_item
        return _id

    @deprecated("use .add_item")
    def add_device(self, *args, **kwargs):
        return self.add_item(*args, **kwargs)

    def _get_item_from_document(self, doc: Dict[str, Any]) -> HappiItem:
        """
        Create a HappiItem given its backend-provided document.

        Parameters
        ----------
        doc : dict
            Document from the backend.

        Returns
        -------
        item : :class:`.HappiItem`
            An item that matches the characteristics given.
        """
        try:
            item = self.create_item(doc["type"], **doc)
        except (KeyError, TypeError) as exc:
            raise EntryError(
                "The information relating to the container class "
                "has been modified to the point where the object "
                "can not be initialized, please load the "
                "corresponding document"
            ) from exc

        # Add the save method to the item
        item.save = lambda: self._store(item, insert=False)
        return item

    def find_item(self, **post):
        """
        Query the database for an individual HappiItem.

        If multiple items are found, only the first is returned.

        Parameters
        ----------
        **post :
            Key-value pairs of search criteria used to find the item.

        Raises
        ------
        SearchError
            If no match for the given information is found.

        Returns
        -------
        item : :class:`.HappiItem`
            A HappiItem instance for the document.
        """
        return self._get_item_from_document(self.find_document(**post))

    @deprecated("use .find_item")
    def find_device(self, **kwargs):
        return self.find_item(**kwargs)

    def load_device(self, use_cache=True, **post):
        """
        Find an item in the database and instantiate it.

        Essentially a shortcut for:

        .. code:: python

            container = client.find_item(name='...')
            item = from_container(container)

        Parameters
        ----------
        post
            Key-value pairs of search criteria passed to
            :meth:`.Client.find_item`.

        use_cache : bool, optional
            Choice to use a cached item. See :meth:`.from_container` for more
            information.

        Returns
        -------
        object
            Instantiated object.
        """
        cntr = self.find_item(**post)
        return from_container(cntr, use_cache=use_cache)

    def change_container(
        self,
        item: HappiItem,
        target: Type[HappiItem],
        edits: Optional[Dict[str, Any]] = None,
        how: str = 'right'
    ) -> Dict[str, Any]:
        """
        Return the kwargs necessary to transfer the information from
        ``item`` into a container ``target``.  Checks are performed to ensure
        the contents are compatible (following enforce requirements in the
        target container)

        This function is built to be a helper function for an interactive
        cli tool, and passes information up accordingly.  If keys are not
        significantly mismatched, this function can be used as is.

        Parameters
        ----------
        item : happi.HappiItem
            HappiItem instance to be transferred to a new container
        target : Type[happi.HappiItem]
            Container to contain new item
        edits : dict[str, Any], optional
            Dictionary of edits to supersede values in original item
        how : str, optional
            Method of resolving the entries between the original item
            and target container.  Can be:
            - "right" : Expect a value for every entry in target container
            - "inner" : Expect values for only entries in BOTH original
            item and target container

        Raises
        ------
        TransferError
            If there is a problem tranferring item into container

        Returns
        -------
        new_kwargs : Dict[str, Any]
            kwargs to pass into a new HappiItem
        """
        edits = edits or {}

        # grab all keys, extraneous and otherwise
        item_post = item.post()
        if how == 'right':
            # Try to fill every value in target
            base_names = target.info_names
        elif how == 'inner':
            # only keys in both original and target
            base_names = [n for n in target.info_names
                          if n in item_post.keys()]
        else:
            raise ValueError(f'Improper merge method: {how}')

        target_entries = {e.key: e for e in target.entry_info}
        new_kwargs = {}
        new_kwargs.update(edits)  # can contain extraneous data
        for name in base_names:
            try:
                # validate every value being placed into target
                # grab edit value, defaulting to item value
                old_val = new_kwargs.get(name, item_post.get(name))
                # no value found in either, continue and handle later
                if old_val is None:
                    continue
                val = target_entries[name].enforce_value(old_val)

                new_kwargs.update({name: val})
            except ValueError as e:
                # Repackage exception with key information
                raise TransferError(e, name)

        # ensure all mandatory info filled
        for req_name in target.mandatory_info:
            if req_name not in new_kwargs:
                msg = f'mandatory field {req_name} missing a value'
                raise TransferError(msg, req_name)

        return new_kwargs

    def validate(self):
        """
        Validate all of the items in the database.

        This is done by attempting to initialize each item and asserting
        their mandatory information is present. Information is written to the
        logger.

        Returns
        -------
        ids : list of str
            List of item ids that have failed verification.
        """

        bad = list()
        logger.debug('Loading database to validate contained devices ...')
        for doc in self.backend.all_items:
            # Try and load device based on database info
            _id = doc.get(self._id_key, "(unknown id)")
            try:
                logger.debug("Attempting to initialize %s...", _id)
                item = self._get_item_from_document(doc)
                logger.debug("Attempting to validate ...")
                self._validate_item(item)
            except Exception as e:
                logger.warning("Failed to validate %s because %s", _id, e)
                bad.append(_id)
            else:
                logger.debug('Successfully validated %s', _id)
        return bad

    @property
    @deprecated("use .all_items")
    def all_devices(self):
        """A list of all contained devices."""
        return self.all_items

    @property
    def all_items(self):
        """A list of all contained items."""
        return [res.item for res in self.search()]

    def __getitem__(self, key):
        """Get an item ID."""
        try:
            item = self._get_item_from_document(self.backend.get_by_id(key))
        except Exception as ex:
            raise KeyError(key) from ex

        return SearchResult(client=self, item=item)

    def __iter__(self):
        for info in self.backend.find({}):
            yield info['_id']

    def __len__(self):
        return len(self.all_items)

    def _maybe_clear_cache(self):
        """Clear the backend cache if not in a retain-cache block."""
        if not self._retain_cache:
            self.backend.clear_cache()

    def _get_search_results(
        self, docs: Sequence[Dict[str, Any]], *, wrap_cls: Optional[type] = None
    ) -> List[SearchResult]:
        """
        Return search results to the user, optionally wrapping with a class.
        """
        wrap_cls = wrap_cls or self._results_wrap_class
        assert wrap_cls is not None

        results = []
        for doc in docs:
            try:
                results.append(
                    wrap_cls(
                        client=self,
                        item=self._get_item_from_document(doc)
                    )
                )
            except Exception as exc:
                logger.warning(
                    "Entry for %s is malformed (%s). Skipping.",
                    doc["name"], exc
                )
        return results

    def search_range(
        self, key: str, start: float, end: Optional[float] = None, **kwargs
    ) -> List[SearchResult]:
        """
        Search the database for an item or items using a numerical range.

        Parameters
        -----------
        key : str
            Database key to search.
        start : float, optional
            Minimum beamline position to include items.
        end : float, optional
            Maximum beamline position to include items.
        **kwargs : optional
            Additional information used to filter through the database
            structured as key-value pairs for the desired pieces of EntryInfo.

        Returns
        -------
        list of SearchResult

        Example
        -------
        .. code::

            gate_valves = client.search_range('z', 0, 100, type='Valve')
            hxr_valves  = client.search_range('z', 0, 100, type='Valve',
                                              beamline='HXR')
        """

        self._maybe_clear_cache()
        items = self.backend.find_range(key, start=start, stop=end,
                                        to_match=kwargs)
        return self._get_search_results(items)

    def search(self, **kwargs):
        """
        Search the database for item(s).

        Parameters
        -----------
        **kwargs
            Information to filter through the database structured as key, value
            pairs for the desired pieces of EntryInfo.

        Returns
        -------
        res : list of SearchResult
            The search results.

        Example
        -------
        .. code::

            gate_valves = client.search(type='Valve')
            hxr_valves  = client.search(type='Valve', beamline='HXR')
        """

        self._maybe_clear_cache()
        items = self.backend.find(kwargs)
        return self._get_search_results(items)

    def search_regex(
        self, flags=re.IGNORECASE, **kwargs
    ) -> List[SearchResult]:
        """
        Search the database for items(s).

        Parameters
        -----------
        flags : int, optional
            Defaulting to ``re.IGNORECASE``, these flags are used for the
            regular expressions passed in.
        **kwargs
            Information to filter through the database structured as key, value
            pairs for the desired pieces of EntryInfo.  Every value is allowed
            to contain a Python regular expression.

        Returns
        -------
        list of SearchResult

        Example
        -------
        .. code::

            gate_valves = client.search_regex(beamline='Valve.*')
            three_valves = client.search_regex(_id='VALVE[123]')
        """

        self._maybe_clear_cache()
        items = self.backend.find_regex(kwargs, flags=flags)
        return self._get_search_results(items)

    def export(self, path=sys.stdout, sep='\t', attrs=None):
        """
        Export the contents of the database into a text file.

        Parameters
        ----------
        path : File Handle
            File-like object to save text file. Defaults to stdout.
        sep : str
            Separator to place inbetween columns of information.
        attrs : iterable
            Attributes to include, these will be a list of values.
        """

        # Load documents
        devs = self.all_items
        logger.info('Creating file at %s ...', path)
        # Load item information
        with path as f:
            for dev in devs:
                try:
                    f.write(sep.join([getattr(dev, attr)
                                      for attr in attrs])
                            + '\n')
                except KeyError as e:
                    logger.error("HappiItem %s was missing attribute %s",
                                 dev.name, e)

    def remove_item(self, item):
        """
        Remove an item from the database.

        Parameters
        ----------
        item : :class:`.HappiItem`
            HappiItem to be removed from the database.
        """

        # HappiItem Check
        if not isinstance(item, HappiItem):
            raise ValueError("Must supply an object of type `HappiItem`")
        logger.info("Attempting to remove %r from the "
                    "collection ...", item)
        # Check that item is in the database
        _id = getattr(item, self._id_key)
        self.backend.delete(_id)

    @deprecated("use .remove_item")
    def remove_device(self, device):
        return self.remove_item(device)

    def _validate_item(self, item):
        """Validate that an item has all of the mandatory information."""
        logger.debug('Validating item %r ...', item)

        # Check type
        if not isinstance(item, HappiItem):
            raise ValueError(f"{item!r} is not a subclass of HappiItem")
        logger.debug('Checking mandatory information has been entered ...')
        # Check that all mandatory info has been entered
        missing = [info.key for info in item.entry_info
                   if not info.optional and
                   info.default == getattr(item, info.key)]
        # Abort initialization if missing mandatory info
        if missing:
            raise EntryError(
                "Missing mandatory information ({}) for {}"
                "".format(", ".join(missing), item.__class__.__name__)
            )
        logger.debug('HappiItem %r has been validated.', item)

    def _store(self, item, insert=False):
        """
        Store a document in the database.

        Parameters
        ----------
        item : :class:`.HappiItem`
            HappiItem to save.
        insert : bool, optional
            Set to `True` if this is a new entry.

        Raises
        ------
        DuplicateError
            When ``_id`` already exists.
        EntryError
            If the item doesn't the correct information.

        Todo
        ----
        Enforce parent is an already entered name
        """

        logger.debug('Loading an item into the collection ...')

        # Validate item is ready for storage
        self._validate_item(item)
        # Grab information from item
        post = item.post()
        # save the old name in case the user is trying to
        # change the 'name' of an entry
        the_old_name = post.get('_id', None)
        # Store creation time
        creation = post.get('creation', ttime.ctime())
        # Clean supplied information
        [post.pop(key) for key in self._client_attrs if key in post]
        # Note that item has some unrecognized metadata
        for key in post.keys():
            if key not in item.info_names:
                logger.debug(
                    "HappiItem %r defines an extra piece of "
                    "information under the keyword %s",
                    item,
                    key,
                )
        # Add metadata from the Client Side

        tpe = containers.registry.entry_for_class(item.__class__)
        post.update({'type': tpe,
                     'creation': creation,
                     'last_edit': ttime.ctime()})

        # Find id
        try:
            _id = post[self._id_key]
        except KeyError:
            raise EntryError('HappiItem did not supply the proper information '
                             'to interface with the database, missing {}'
                             ''.format(self._id_key))
        # In case we want to update the name of an entry
        # We want to add a new entry, and delete the old one
        if the_old_name and the_old_name != post[self._id_key]:
            # Store information for the new entry
            logger.info('Saving new entry %s ...', _id)
            self.backend.save(_id, post, insert=True)
            # Remove the information for the old entry
            logger.info('Removing old entry %s ...', the_old_name)
            self.backend.delete(the_old_name)
        else:
            # Store information
            logger.info('Adding / Modifying information for %s ...', _id)
            self.backend.save(_id, post, insert=insert)
        return _id

    @classmethod
    def from_config(cls, cfg=None):
        """
        Create a client from a configuration file specification.

        Configuration files looking something along the lines of:

        .. code::

            [DEFAULT]
            path=path/to/my/db.json

        All key value pairs will be passed directly into backend construction
        with the exception of the key ``backend`` which can be used to specify
        a specific type of backend if this differs from the configured default.

        Parameters
        ----------
        cfg : str, optional
            Path to a configuration file. If not entered, :meth:`.find_config`
            will be use.
        """

        # Find a configuration file
        if not cfg:
            cfg = cls.find_config()

        if not os.path.exists(cfg):
            raise RuntimeError(f'happi configuration file not found: {cfg!r}')

        # Parse configuration file
        cfg_parser = configparser.ConfigParser()
        cfg_file = cfg_parser.read(cfg)
        logger.debug("Loading configuration file at %r", cfg_file)
        db_kwargs = cfg_parser['DEFAULT']
        # If a backend is specified use it, otherwise default
        if 'backend' in db_kwargs:
            db_str = db_kwargs.pop('backend')
            try:
                backend = BACKENDS[db_str]
            except KeyError:
                raise RuntimeError(
                    f'Happi backend {db_str!r} unavailable'
                ) from None
        else:
            backend = DEFAULT_BACKEND

        logger.debug(
            "Using Happi backend %r with kwargs %s",
            backend, db_kwargs
        )

        # Create our database with provided kwargs
        try:
            database = backend(**db_kwargs, cfg_path=cfg)
            return cls(database=database)
        except Exception as ex:
            raise RuntimeError(
                f'Unable to instantiate the client. Please verify that '
                f'your HAPPI_CFG points to the correct file and has '
                f'the required configuration settings. In {cfg!r}, found '
                f'settings: {dict(db_kwargs)}.'
            ) from ex

    @staticmethod
    def find_config():
        """
        Search for a ``happi`` configuration file.

        We first query the environment variable ``$HAPPI_CFG`` to see if this
        points to a specific configuration file. If this is not present, the
        variable set by ``$XDG_CONFIG_HOME`` or if  that is not set
        ``~/.config``

        Returns
        -------
        path : str
            Absolute path to configuration file.

        Raises
        ------
        EnvironmentError
            If no configuration file can be found by the methodology detailed
            above.
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
        List all choices for a given field.

        Parameters
        ----------
        field : string
            Field name to list all possible choices for
            i.e 'beamline', 'name', 'z', 'prefix', etc.

        Raises
        ------
        SearchError
            If no items in the database have an entry for the given field.

        Returns
        -------
        field_choices : list
            List of choices for a given field that are in the database.
        """

        field_choices = set()
        for dev in self.all_items:
            try:  # Want to ignore error if 'dev' doesn't have 'field'
                choice = getattr(dev, field)
                field_choices.add(choice)
            except AttributeError:
                pass
        if len(field_choices) == 0:
            raise SearchError('No entries found with given field')
        return field_choices
