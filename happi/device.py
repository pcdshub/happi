import copy
import re
import sys
import logging
import warnings

from collections import OrderedDict
from prettytable import PrettyTable

from .errors import ContainerError

logger = logging.getLogger(__name__)


# For back-compat to <py3.7
try:
    from re import Pattern
except ImportError:
    from re import _pattern_type as Pattern


class EntryInfo(object):
    """
    A piece of information related to a specific device

    These are entered as class attributes for a given device container. They
    help control the information entered into a device

    Parameters
    ----------
    doc : str
        A short string to document the device

    optional : bool, optional
        By default all EntryInfo is optional, but in certain cases you may want
        to demand a particular piece of information upon initialization

    enforce : type, list, compiled regex, optional
        Specify that all entered information is entered in a specific format.
        This can either by a Python type i.e. int, float e.t.c., a list of
        acceptable values, or a compiled regex pattern i.e ``re.compile(...)``

    default : optional
        A default value for the trait to have if the user does not specify.
        Keep in mind that this should be the same type as ``enforce`` if you
        are demanding a certain type.

    Raises
    ------
    ContainerError:
        If there is an error with the way the enforced value interacts with its
        default value, or if the piece of information entered is unenforcable
        based on the the settings

    Example
    ------
    .. code::

        class MyDevice(Device):

            my_field = EntryInfo('My generated field')
            number   = EntryInfo('Device number', enforce=int, default=0)
    """
    def __init__(self, doc=None, optional=True, enforce=None, default=None):
        self.key = None  # Set later by parent class
        self.doc = doc
        self.enforce = enforce
        self.optional = optional

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
        Enforce the rules of the EntryInfo

        Parameters
        ----------
        value

        Returns
        -------
        value :
            Identical to the provided value except it may have been converted
            to the correct type

        Raises
        ------
        ValueError:
            If the value is not the correct type, or does not match the pattern
        """
        if not self.enforce or value is None:
            return value

        elif isinstance(self.enforce, type):
            # Try and convert to type, otherwise raise ValueError
            return self.enforce(value)

        elif isinstance(self.enforce, (list, tuple, set)):
            # Check that value is in list, otherwise raise ValueError
            if value not in self.enforce:
                raise ValueError('{} was not found in the enforce list {}'
                                 ''.format(self.key, self.enforce))
            return value

        elif isinstance(self.enforce, Pattern):
            # Try and match regex patttern, otherwise raise ValueError
            if not self.enforce.match(value):
                raise ValueError('{} did not match the enforced pattern {}'
                                 ''.format(self.key, self.enforce.pattern))
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
                         enforce=self.enforce, default=self.default)


class InfoMeta(type):

    def __new__(cls, name, bases, clsdict):
        clsobj = super(InfoMeta, cls).__new__(cls, name, bases, clsdict)

        # These attributes are used by device so can not be overwritten
        RESERVED_ATTRS = ['info_names', 'entry_info',
                          'mandatory_info', '_info_attrs',
                          'post', 'save', 'creation', '_id',
                          'last_edit']

        # Create dict to hold information
        clsobj._info_attrs = OrderedDict()

        # Handle multiple inheritance
        for base in reversed(bases):

            if not hasattr(base, '_info_attrs'):
                continue

            for attr, info in base._info_attrs.items():
                clsobj._info_attrs[attr] = info

        # Load from highest classEntry
        for attr, value in clsdict.items():
            if isinstance(value, EntryInfo):
                if attr in RESERVED_ATTRS:
                    raise TypeError("The attribute name %r is used by the "
                                    "Device class and can not be used as "
                                    "a name for EntryInfo. Choose a different "
                                    "name" % attr)

                clsobj._info_attrs[attr] = value

        # Notify Info of key names
        for attr, info in clsobj._info_attrs.items():
            info.key = attr
        # Create docstring information
        for info in clsobj._info_attrs.values():
            info.__doc__ = info.make_docstring(clsobj)
        # Store Entry Information
        clsobj.entry_info = list(clsobj._info_attrs.values())

        return clsobj


class HappiItem(metaclass=InfoMeta):
    """
    The smallest description of an object that can be entered in ``happi``

    The class does not need to be intialized with any specific piece of
    information except a name, but all of the attributes listed by
    :attr:`HappiItem.info_names` can be used to assign values to
    :class:`.EntryInfo` upon initialization.  Pieces of information that are
    deemed mandatory by the class must be filled in before the device is loaded
    into the database. See :attr:`Device.mandatory_info` to see which
    attributes are neccesary.

    Additional metadata can be given to the device in the form of keywords on
    initialization, this information is kept in the :attr:`.extraneous`
    attribute, and will be saved in to the database as long as it does not
    clash with an existing piece of metadata that the client uses to organize
    devices.

    Attributes
    ----------
    entry_info : list
        A list of all the :class:`.EntryInfo` associated with the device

    extraneous : dict
        Storage for information supplied during initialization that does not
        correspond to a specific EntryInfo

    Raises
    ------
    EntryError:
        If a piece of information supplied at startup is of the incorrect type

    ContainerError:
        If one of the pieces of :class:`.EntryInfo` has a default value of the
        incorrect type

    Example
    -------
    .. code ::

        d = HappiItem(name = 'my_device',         #Alias name for device
                      note  = 'Example',          #Piece of arbitrary metadata
                     )
    """
    name = EntryInfo('Shorthand name for the device',
                     optional=False, enforce=str)
    device_class = EntryInfo("Python class that represents the Device",
                             enforce=str)
    args = EntryInfo("Arguments to pass to device_class",
                     enforce=list, default=[])
    kwargs = EntryInfo("Keyword arguments to pass to device_class",
                       enforce=dict, default={})
    active = EntryInfo('Whether the device is actively deployed',
                       enforce=bool, default=True)
    parent = EntryInfo('If the device is a component of another, '
                       'enter the name', enforce=str)

    def __init__(self, **kwargs):
        # Load given information into device class
        for info in self.entry_info:
            if info.key in kwargs.keys():
                setattr(self, info.key, kwargs.pop(info.key))
            else:
                setattr(self, info.key, info.default)
        # Handle additional information
        if kwargs:
            logger.debug('Additional information for %s was defined %s',
                         self.name, ', '.join(kwargs.keys()))
            self.extraneous = kwargs
        else:
            self.extraneous = {}

    @property
    def info_names(self):
        """
        Names of all :class:`.EntryInfo` for the device
        """
        return [info.key for info in self.entry_info]

    @property
    def mandatory_info(self):
        """
        Mandatory information for the device to be initialized
        """
        return [info.key for info in self.entry_info if not info.optional]

    def show_info(self, handle=sys.stdout):
        """
        Show the device information in a PrettyTable

        Parameters
        ----------
        handle : file-like, optional
            Option to write to a file-like object
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
        Create a document to be loaded into the happi database

        Returns
        -------
        post : dict
            Dictionary of all contained information
        """
        # Grab all the specified information
        post = dict([(key, getattr(self, key)) for key in self.info_names])

        # Add additional metadata
        if self.extraneous:
            post.update(self.extraneous)

        return post

    @property
    def screen(self):
        warnings.warn("The 'screen' keyword is no longer used in Happi as it "
                      "lacks specificity. Use one of detailed_screen, "
                      "embedded_screen, or engineering screen instead")
        return self.detailed_screen

    def save(self):
        """
        Overwritten when the device is loaded from the client
        """
        raise NotImplementedError

    def __repr__(self):
        return '{} (name={})'.format(self.__class__.__name__,
                                     self.name)

    def __eq__(self, other):
        return (self.post() == other.post())


class Device(HappiItem):
    """
    A Generic Device

    Meant for any object will be loaded to represent a physical object in the
    controls system. Contains information on the physical location of the
    device as well as various
    """
    prefix = EntryInfo('A base PV for all related records',
                       optional=False, enforce=str)
    beamline = EntryInfo('Section of beamline the device belongs',
                         optional=False, enforce=str)
    z = EntryInfo('Beamline position of the device',
                  enforce=float, default=-1.0)
    stand = EntryInfo('Acronym for stand, must be three alphanumeric '
                      'characters', enforce=re.compile(r'[A-Z0-9]{3}$'))
    detailed_screen = EntryInfo('The absolute path to the main control screen',
                                enforce=str)
    embedded_screen = EntryInfo('The absolute path to the '
                                'embedded control screen',
                                enforce=str)
    engineering_screen = EntryInfo('The absolute path to '
                                   'the engineering control screen',
                                   enforce=str)
    system = EntryInfo('The system the device is involved with, i.e '
                       'Vacuum, Timing e.t.c',
                       enforce=str)
    macros = EntryInfo("The EDM macro string asscociated with the "
                       "with the device. By using a jinja2 template, "
                       "this can reference other EntryInfo keywords.",
                       enforce=str)
    lightpath = EntryInfo("If the device should be included in the "
                          "LCLS Lightpath", enforce=bool, default=False)
    documentation = EntryInfo("Relevant documentation for the Device",
                              enforce=str)
    args = copy.copy(HappiItem.args)
    args.default = ['{{prefix}}']
    kwargs = copy.copy(HappiItem.kwargs)
    args.default = {'name': '{{name}}'}

    def __repr__(self):
        return '{} (name={}, prefix={}, z={})'.format(
                                    self.__class__.__name__,
                                    self.name,
                                    self.prefix,
                                    self.z)
