import logging
import textwrap
from collections import OrderedDict

logger = logging.getLogger(__name__)

class EntryInfo:
    """
    A piece of information related to a specific device
    """
    def __init__(self, doc=None, optional=True, enforce=None, default=None):
        self.key      = None #Set later by parent class
        self.doc      = doc
        self.enforce  = enforce
        self.optional = optional
        self.default  = default


    def make_docstring(self, parent_class):
        """
        Create a docstring if one was not supplied
        """
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
         for attr, value in clsdict.items()
            if isinstance(value, EntryInfo):
                if attr in RESERVED_ATTRS:
                    raise TypeError("The attribute name %r is used by the
                                     Device class and can not be used as
                                     a name for EntryInfo. Choose a different
                                     name" % attr)

                clsobj._info_attrs[attr] = value

        #Notify Info of key names
        for attr, info in clsobj._info_attrs.items():
            info.key = attr

        #Create docstring information
        for info in clsobj._info_attrs.values():
            info.__doc__ = info.make_docstring(clsobj)

        #Store Entry Information
        clsobj.entry_info = list(clsobj._info_attrs.values())


class Device:
    """
    A Generic Device
    """
    alias           = EntryInfo('Shorthand alias for the device',optional=False)
    z               = EntryInfo('Beamline position of the device'optional=False,enforce=float)
    base            = EntryInfo('A base PV for all related records',optional=False)
    beamline        = EntryInfo('Section of beamline the device belongs',optional=False)
    stand           = EntryInfo('Acronym for stand')
    main_screen     = EntryInfo('The absolute path to the main control screen')
    embedded_screen = EntryInfo('The absolute path to an embeddable screen')
    parent          = EntryInfo('If the device is a component of another, enter
                                 the alias')


    def __init__(self, **kwargs):

        #Check that all mandatory info has been entered
        missing = [info for info in self.mandatory_info
                   if info not kwargs.keys()]

        #Abort initialization if missing mandatory info
        if missing:
            missing = ', '.join(missing)
            raise ValueError('Missing mandatory information ({}) for
                              Device'.format(missing))

        #Load given information into device class
        for info in self.entry_info:
            if info.key in kwargs.keys():
                setattr(self, info.key, kwargs.pop(info.key))

            else:
                setattr(self, info.key, info.default)


        #Handle additional information
        if kwargs:
            logging.info('Additional information for {} was defined
                          {}'.format(self.alias, ', '.join(kwargs.keys()))

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


class PIM(Device):
    camera = EntryInfo('Camera name')
