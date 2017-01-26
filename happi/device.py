import logging
import textwrap
from collections import OrderedDict

from .utils import EntryError

logger = logging.getLogger(__name__)

class EntryInfo:
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

    enforce : type, optional
        Specify that all entered information is of a specific Python type. The
        device upon intialiation will try and convert the given value to the
        enforced type, raises a ``ValueError`` if unsuccessful. If left
        unspecified any type will be expected

    default : optional
        A default value for the trait to have if the user does not specify.
        Keep in mind that this should be the same type as ``enforce`` if you
        are demanding a certain type.

    Example
    ------
    .. code::

        class MyDevice(Device):

            my_field = EntryInfo('My generated field')
            number   = EntryInfo('Device number', enforce=int, default=0)

    Raises
    ------
    EntryError:
        If the default value does not match the specified ``enforce`` type and
        the EntryInfo is optional
    """
    def __init__(self, doc=None, optional=True, enforce=None, default=None):
        self.key      = None #Set later by parent class
        self.doc      = doc
        self.enforce  = enforce
        self.optional = optional
        self.default  = default

        #Check that the 
        if enforce and optional:
            try:
                enforce(default)
            except ValueError:
                raise EntryError('Default value must match the enforced type')


    def make_docstring(self, parent_class):
        if self.doc is not None:
            return self.doc

        doc = ['{} attribute'.format(self.__class__.__name__),
               '::',
               '',
              ]

        doc.append(textwrap.indent(repr(self), prefix =' '*4))
        doc.append('')
        return '\n'.join(doc)


    def __get__(self, instance, owner):

        if instance is None:
            return self

        return instance.__dict__[self.key]


    def __set__(self, instance, value):
        if self.enforce:
            value = self.enforce(value)

        instance.__dict__[self.key] = value


    def __repr__(self):
        if self.enforce:
            enforce = self.enforce.__name__

        else:
            enforce = None

        return 'EntryInfo {} (optional={}, type={}, default={})'.format(self.key,
                                                                        self.optional,
                                                                        enforce,
                                                                        self.default)


class InfoMeta(type):


    def __new__(cls, name, bases, clsdict):
        clsobj = super().__new__(cls, name, bases, clsdict)

        #These attributes are used by device so can not be overwritten
        RESERVED_ATTRS = ['info_names','entry_info',
                          'mandatory_info','_info_attrs']

        #Create dict to hold information
        clsobj._info_attrs = OrderedDict()

        #Handle multiple inheritance
        for base in reversed(bases):

            if not hasattr(base, '_info_attrs'):
                continue

            for attr, info in base._info_attrs.items():
                clsobj._info_attrs[attr] = info

        #Load from highest classEntry
        for attr, value in clsdict.items():
            if isinstance(value, EntryInfo):
                if attr in RESERVED_ATTRS:
                    raise TypeError("The attribute name %r is used by the "
                                    "Device class and can not be used as "
                                    "a name for EntryInfo. Choose a different "
                                    "name" % attr)

                clsobj._info_attrs[attr] = value

        #Notify Info of key names
        for attr, info in clsobj._info_attrs.items():
            info.key = attr

        #Create docstring information
        for info in clsobj._info_attrs.values():
            info.__doc__ = info.make_docstring(clsobj)

        #Store Entry Information
        clsobj.entry_info = list(clsobj._info_attrs.values())

        return clsobj


class Device(metaclass=InfoMeta):
    """
    A Generic Device

    Attributes
    ----------
    entry_info : list
        A list of all the ``Entry_Info`` associated with the device

    extraneous : dict
        Storage for information supplied during initialization that does not
        correspond to a specific EntryInfo

    Raises
    ------
    EntryError:
        Raised if a piece of mandatory information is unspecified
    """
    alias           = EntryInfo('Shorthand alias for the device',optional=False)
    z               = EntryInfo('Beamline position of the device',optional=False,enforce=float)
    base            = EntryInfo('A base PV for all related records',optional=False)
    beamline        = EntryInfo('Section of beamline the device belongs',optional=False)
    stand           = EntryInfo('Acronym for stand')
    main_screen     = EntryInfo('The absolute path to the main control screen')
    embedded_screen = EntryInfo('The absolute path to an embeddable screen')
    parent          = EntryInfo('If the device is a component of another, '
                                'enter the alias')

    def __init__(self, **kwargs):

        #Check that all mandatory info has been entered
        missing = [info for info in self.mandatory_info
                   if info not in kwargs.keys()]

        #Abort initialization if missing mandatory info
        if missing:
            missing = ', '.join(missing)
            raise EntryError('Missing mandatory information ({}) for '
                             'Device'.format(missing))

        #Load given information into device class
        for info in self.entry_info:
            if info.key in kwargs.keys():
                setattr(self, info.key, kwargs.pop(info.key))

            else:
                setattr(self, info.key, info.default)


        #Handle additional information
        if kwargs:
            logging.info('Additional information for {} was defined '
                         '{}'.format(self.alias, ', '.join(kwargs.keys())))
            self.extraneous = kwargs


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


    def __repr__(self):
        return '{} {} (base={}, z={})'.format(self.__class__.__name__,
                                              self.alias,
                                              self.base,
                                              self.z)
