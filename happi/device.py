import copy
import logging
import re
import warnings

from .item import EntryInfo, HappiItem

logger = logging.getLogger(__name__)


class Device(HappiItem):
    """
    Deprecated due to confusing naming

    Original docstring:
    A Generic Device container

    Meant for any object will be loaded to represent a physical object in the
    controls system. Contains information on the physical location of the
    device as well as various
    """
    prefix = EntryInfo('A base PV for all related records',
                       optional=False, enforce=str)
    beamline = EntryInfo('Section of beamline the device belongs',
                         optional=False, enforce=str)
    location_group = EntryInfo('Grouping parameter for device location',
                               optional=False, enforce=str)
    functional_group = EntryInfo('Grouping parameter for device function',
                                 optional=False, enforce=str)
    z = EntryInfo('Beamline position of the device',
                  enforce=float, default=-1.0)
    stand = EntryInfo('Acronym for stand, must be three alphanumeric '
                      'characters like an LCLSI stand (e.g. DG3) or follow '
                      'the LCLSII stand naming convention (e.g. L0S04).',
                      enforce=re.compile(r'[A-Z0-9]{3}$|[A-Z][0-9]S[0-9]{2}$'))
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
    parent = EntryInfo('If the device is a component of another, '
                       'enter the name', enforce=str)
    args = copy.copy(HappiItem.args)
    args.default = ['{{prefix}}']
    kwargs = copy.copy(HappiItem.kwargs)
    kwargs.default = {'name': '{{name}}'}

    def __init__(self, *args, **kwargs):
        warnings.warn("happi.device.Device is deprecated. Please use "
                      "OphydItem or LCLSItem.", DeprecationWarning)
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return '{} (name={}, prefix={}, z={})'.format(
                                    self.__class__.__name__,
                                    self.name,
                                    self.prefix,
                                    self.z)

    @property
    def screen(self):
        warnings.warn("The 'screen' keyword is no longer used in Happi as it "
                      "lacks specificity. Use one of detailed_screen, "
                      "embedded_screen, or engineering screen instead",
                      DeprecationWarning)
        return self.detailed_screen
