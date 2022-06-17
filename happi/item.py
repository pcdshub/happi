import collections
import copy
import logging
import sys
from collections import OrderedDict

from prettytable import PrettyTable

from .errors import ContainerError, EnforceError
from .utils import is_valid_identifier_not_keyword

logger = logging.getLogger(__name__)

# For back-compat to <py3.7
try:
    from re import Pattern
except ImportError:
    from re import _pattern_type as Pattern


class EntryInfo:
    """
    A piece of information related to a specific device.

    These are entered as class attributes for a given device container. They
    help control the information entered into a device.

    Parameters
    ----------
    doc : str
        A short string to document the device.
    optional : bool, optional
        By default all EntryInfo is optional, but in certain cases you may want
        to demand a particular piece of information upon initialization.
    enforce : type, list, compiled regex, or function, optional
        Specify that all entered information is entered in a specific format.
        This can either by a Python type i.e. int, float e.t.c., a list of
        acceptable values, a compiled regex pattern i.e ``re.compile(...)``,
        or custom handling by passing a function that takes in one argument,
        the value. This function must do one of: return the value back as-is,
        return the value back converted to a corrected form, or raise a
        EnforceError.
    default : optional
        A default value for the trait to have if the user does not specify.
        Keep in mind that this should be the same type as ``enforce`` if you
        are demanding a certain type.
    enforce_doc : str, optional
        A human-readable explanation of the enforce field.  Will be printed
        if the entered information does not follow the ``enforce`` type

    Raises
    ------
    ContainerError
        If there is an error with the way the enforced value interacts with its
        default value, or if the piece of information entered is unenforcable
        based on the the settings.

    Example
    ------
    .. code::

        class MyItem(HappiItem):
            my_field = EntryInfo('My generated field')
            number   = EntryInfo('Device number', enforce=int, default=0,
                                 enforce_doc='This must be a number')
    """

    def __init__(self, doc=None, optional=True, enforce=None,
                 default=None, enforce_doc=None):
        self.key = None  # Set later by parent class
        self.doc = doc
        self.enforce = enforce
        self.optional = optional
        self.enforce_doc = str(enforce_doc or '')

        # Explicitly set default to None b/c this is how we ensure mandatory
        # information was set
        if optional:
            self.default = default
        else:
            self.default = None

        # Check that default value is correct type
        try:
            self.enforce_value(default)
        except ValueError:
            raise ContainerError('Default value must match the enforced type')

    def enforce_value(self, value):
        """
        Enforce the rules of the EntryInfo.

        Accepts a ``value``, verifies that it meets the criteria specified in
        the ``enforce`` attribute, and returns the same value, except that it
        will be converted to the correct type if ``enforce`` is a type.

        Raises
        ------
        EnforceError
            If the value is not the correct type, or does not match the
            pattern.
        """
        if not self.enforce or value is None:
            return value

        elif self.enforce is bool and isinstance(value, str):
            # Special case for booleans, since the value may come in as a
            # string, and bool('False') evaluates to True
            true_values = ['true', 't', 'yes', 'y']
            false_values = ['false', 'f', 'no', 'n']
            if value.lower() in true_values:
                return True
            elif value.lower() in false_values:
                return False
            else:
                raise EnforceError(f'{value} as a string is not interpretable '
                                   f'as a boolean.  {self.enforce_doc}')

        elif callable(self.enforce):
            # Try and convert to type or custom handling
            # Otherwise raise EnforceError for types, custom handling otherwise
            try:
                return self.enforce(value)
            except ValueError as e:
                if self.enforce_doc:
                    raise EnforceError(self.enforce_doc) from e
                else:
                    raise EnforceError(e)

        elif isinstance(self.enforce, (list, tuple, set)):
            # Check that value is in list, otherwise raise EnforceError
            if value not in self.enforce:
                raise EnforceError(f'{value} was not found in the enforce '
                                   f'list {self.enforce}. {self.enforce_doc}')
            return value

        elif isinstance(self.enforce, Pattern):
            # Try and match regex patttern, otherwise raise EnforceError
            try:
                if not self.enforce.match(value):
                    raise EnforceError(
                        f'{self.key}={value!r} did not match the enforced '
                        f'pattern: ({self.enforce.pattern}). '
                        f'{self.enforce_doc}'
                    )
            except TypeError as e:
                raise EnforceError(e)

            return value

        # Invalid enforcement
        else:
            raise ContainerError('EntryInfo {} has an invalid enforce'
                                 ''.format(self.key))

    def make_docstring(self, parent_class):
        if self.doc is not None:
            return self.doc

        doc = ['{} attribute'.format(self.__class__.__name__),
               '::',
               '',
               ]

        doc.append(repr(self))
        doc.append('')
        return '\n'.join(doc)

    def __get__(self, instance, owner):
        if instance is None:
            return self

        return instance.__dict__[self.key]

    def __set__(self, instance, value):
        instance.__dict__[self.key] = self.enforce_value(value)

    def __repr__(self):
        return 'EntryInfo {} (optional={}, default={})'.format(self.key,
                                                               self.optional,
                                                               self.default)

    def __copy__(self):
        return EntryInfo(doc=self.doc, optional=self.optional,
                         enforce=self.enforce, default=self.default,
                         enforce_doc=self.enforce_doc)


class _HappiItemBase:
    def __init_subclass__(cls, **kargs):
        # These attributes are not to be overwritten by subclasses
        RESERVED_ATTRS = [
            '_id', '_info_attrs',
            'creation', 'entry_info', 'info_names', 'last_edit',
            'mandatory_info', 'post', 'save',
            ]

        # Create dict to hold information
        cls._info_attrs = OrderedDict()

        # Handle multiple inheritance
        for base in reversed(cls.mro()[1:]):
            if not hasattr(base, '_info_attrs'):
                continue

            for attr, info in base._info_attrs.items():
                cls._info_attrs[attr] = info

        # Load from highest classEntry
        entries = [(attr, entry)
                   for attr, entry in cls.__dict__.items()
                   if isinstance(entry, EntryInfo)
                   ]

        for attr, entry in entries:
            if attr in RESERVED_ATTRS:
                raise TypeError(
                    f"The attribute name {attr} is used by the HappiItem "
                    f"class and cannot be used as a name for EntryInfo. "
                    f"Choose a different name."
                )

            cls._info_attrs[attr] = entry

        # Notify Info of key names
        for attr, info in cls._info_attrs.items():
            info.key = attr

        # Create docstring information
        for info in cls._info_attrs.values():
            info.__doc__ = info.make_docstring(cls)

        # Store Entry Information
        cls.entry_info = list(cls._info_attrs.values())
        cls.info_names = [info.key for info in cls.entry_info]
        cls.mandatory_info = [info.key for info in cls.entry_info
                              if not info.optional]


class HappiItem(_HappiItemBase, collections.abc.Mapping):
    """
    The smallest description of an object that can be entered in ``happi``.

    The class does not need to be intialized with any specific piece of
    information except a name, but all of the attributes listed by
    :attr:`HappiItem.info_names` can be used to assign values to
    :class:`.EntryInfo` upon initialization.  Pieces of information that are
    deemed mandatory by the class must be filled in before the device is loaded
    into the database. See :attr:`.mandatory_info` to see which
    attributes are neccesary.

    Additional metadata can be given to the device in the form of keywords on
    initialization, this information is kept in the :attr:`.extraneous`
    attribute, and will be saved in to the database as long as it does not
    clash with an existing piece of metadata that the client uses to organize
    devices.

    Attributes
    ----------
    entry_info : list
        A list of all the :class:`.EntryInfo` associated with the device.
    extraneous : dict
        Storage for information supplied during initialization that does not
        correspond to a specific EntryInfo.

    Raises
    ------
    EntryError
        If a piece of information supplied at startup is of the incorrect type.
    ContainerError
        If one of the pieces of :class:`.EntryInfo` has a default value of the
        incorrect type.

    Example
    -------
    .. code ::

        d = HappiItem(name = 'my_device',         # Alias name for device
                      note  = 'Example',          # Piece of arbitrary metadata
                     )
    """

    name = EntryInfo("Shorthand Python-valid name for the Python instance",
                     optional=False,
                     enforce=is_valid_identifier_not_keyword)
    device_class = EntryInfo("Python class that represents the instance",
                             enforce=str)
    args = EntryInfo("Arguments to pass to device_class",
                     enforce=list, default=[])
    kwargs = EntryInfo("Keyword arguments to pass to device_class",
                       enforce=dict, default={})
    active = EntryInfo('Whether the instance is actively deployed',
                       enforce=bool, default=True)
    documentation = EntryInfo("Relevant documentation for the instance",
                              enforce=str)

    def __init__(self, **kwargs):
        # Load given information into device class
        for info in self.entry_info:
            if info.key in kwargs.keys():
                setattr(self, info.key, kwargs.pop(info.key))
            else:
                setattr(self, info.key, info.default)
        # Handle additional information
        self.extraneous = kwargs
        if kwargs:
            logger.debug("Additional information for %s was defined %s",
                         self.name, ', '.join(self.extraneous))

    def show_info(self, handle=sys.stdout):
        """
        Show the device instance information in a PrettyTable.

        Parameters
        ----------
        handle : file-like, optional
            Option to write to a file-like object.
        """

        pt = PrettyTable(['EntryInfo', 'Value'])
        pt.align = 'r'
        pt.align['EntryInfo'] = 'l'
        pt.align['Value'] = 'l'
        pt.float_format = '8.5'

        # Gather all device information, do not show private
        # information that begins with an underscore
        show_info = self.post()
        public_keys = sorted([key for key in show_info.keys()
                              if not key.startswith('_')])
        for key in public_keys:
            pt.add_row([key, show_info[key]])

        print(pt, file=handle)

    def post(self):
        """
        Create a document to be loaded into the happi database.

        Returns
        -------
        post : dict
            Dictionary of all contained information.
        """

        # Grab all the specified information
        post = dict([(key, getattr(self, key)) for key in self.info_names])

        # Add additional metadata
        if self.extraneous:
            post.update(self.extraneous)

        return post

    def __getitem__(self, item):
        return self.post()[item]

    def __iter__(self):
        yield from self.info_names
        if self.extraneous:
            yield from self.extraneous

    def __len__(self):
        return len(self.post())

    def __copy__(self):
        return self.__deepcopy__({})

    def __deepcopy__(self, memo):
        device_info = copy.deepcopy(dict(self))
        return type(self)(**device_info)

    def save(self):
        """Overwritten when the device instance is loaded from the client."""
        raise NotImplementedError

    def __repr__(self):
        return '{} (name={})'.format(self.__class__.__name__,
                                     self.name)

    def __eq__(self, other):
        return (self.post() == other.post())


class OphydItem(HappiItem):
    prefix = EntryInfo("A base PV for all related records",
                       optional=False, enforce=str)

    args = copy.copy(HappiItem.args)
    args.default = ['{{prefix}}']
    kwargs = copy.copy(HappiItem.kwargs)
    kwargs.default = {'name': '{{name}}'}
