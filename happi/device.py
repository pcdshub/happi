###################
# Standard Packages
###################
import re
import logging
import textwrap

from collections import OrderedDict

###################
# Module Packages
###################
from .errors import ContainerError

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
        self.key      = None #Set later by parent class
        self.doc      = doc
        self.enforce  = enforce
        self.optional = optional

        #Explicitly set default to None b/c this is how we ensure mandatory
        #information was set
        if optional:
            self.default  = default

        else:
            self.default = None

        #Check that default value is correct type
        try:
            self.enforce_value(default)

        except ValueError:
            raise ContainerError('Default value must match the enforced type')


    def enforce_value(self, value):
        if not self.enforce or value == None:
            return value

        elif isinstance(self.enforce, type):
            #Try and convert to type, otherwise raise ValueError
            return self.enforce(value)

        elif isinstance(self.enforce, (list,tuple,set)):
            #Check that value is in list, otherwise raise ValueError
            if value not in self.enforce:
                raise ValueError('{} was not found in the enforce list {}'
                                 ''.format(self.key, self.enforce))
            return value

        elif isinstance(self.enforce, re._pattern_type):
            #Try and match regex patttern, otherwise raise ValueError
            if not self.enforce.match(value):
                raise ValueError('{} did not match the enforced pattern {}'
                                ''.format(self.key, self.enforce.pattern))
            return value

        #Invalid enforcement
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

        doc.append(textwrap.indent(repr(self), prefix =' '*4))
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
        clsobj = super().__new__(cls, name, bases, clsdict)

        #These attributes are used by device so can not be overwritten
        RESERVED_ATTRS = ['info_names','entry_info',
                          'mandatory_info','_info_attrs',
                          'post', 'save', 'creation', '_id',
                          'last_edit']

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
    A Generic Device Container

    The class does not need to be intialized with any specific piece of
    information, but all of the attributes listed by :attr:`Device.info_names`
    can be used to assign values to :class:`.EntryInfo` upon initialization.
    Pieces of information that are deemed mandatory by the class must be filled
    in before the device is loaded into the database. See
    :attr:`Device.mandatory_info` to see which attributes are neccesary.

    Additional metadata can be given to the device in the form of keywords
    on initialization, this information is kept in the :attr:`.extraneous`
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

        d = Device(alias = 'my_device',      #Alias name for device
                   base  = 'CXI:DG2:DEV:01', #Base PV for device
                   note  = 'Example',        #Piece of arbitrary metadata
                  )
    .. todo::

        Add a PrettyTable output of current information
    """

    #Entry Info
    alias           = EntryInfo('Shorthand alias for the device',
                                optional=False, enforce=str)
    base            = EntryInfo('A base PV for all related records',
                                optional=False, enforce=str)
    beamline        = EntryInfo('Section of beamline the device belongs',
                                optional=False, enforce=str)
    z               = EntryInfo('Beamline position of the device',
                                enforce=float, default = -1.0)
    stand           = EntryInfo('Acronym for stand, must be three alphanumeric '
                                'characters',
                                enforce=re.compile(r'[A-Z0-9]{3}$'))
    main_screen     = EntryInfo('The absolute path to the main control screen',
                                enforce=str)
    embedded_screen = EntryInfo('The absolute path to an embeddable screen',
                                enforce=str)
    system          = EntryInfo('The system the device is involved with, i.e '
                                'Vacuum, Timing e.t.c',
                                enforce=str)
    parent          = EntryInfo('If the device is a component of another, '
                                'enter the alias',
                                enforce=str)

    def __init__(self, **kwargs):
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


    def post(self):
        """
        Create a document to be loaded into the MongoDB

        Returns
        -------
        post : dict
            Dictionary of all contained information
        """
        #Grab all the specified information
        post = dict([(key, getattr(self,key)) for key in self.info_names])


        #Add additional metadata
        if self.extraneous:
            post.update(self.extraneous)

        return post


    def save(self):
        """
        Overwritten when the device is loaded from the client
        """
        raise NotImplementedError


    def __repr__(self):
        return '{} {} (base={}, z={})'.format(self.__class__.__name__,
                                              self.alias,
                                              self.base,
                                              self.z)
