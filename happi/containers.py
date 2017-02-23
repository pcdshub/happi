"""
Define subclasses of Device for specific hardware.
"""
import re
from .device import Device, EntryInfo


# Broad device categories
class MPS(Device):
    """
    Parent class for devices that are in MPS.
    """
    mps = EntryInfo('MPS PV associated with the Device',
                    optional=False, enforce=str)
    veto = EntryInfo('Whether MPS considers this a veto device',
                     enforce=bool, default=False)


class Vacuum(Device):
    """
    Parent class for devices in the vacuum system.
    """
    def __init__(self, *args, **kwargs):
        self.system.default = 'vacuum'
        super().__init__(*args, **kwargs)


class Diagnostic(Device):
    """
    Parent class for devices that are used as diagnostics.
    """
    data = EntryInfo('PV that gives us the diagnostic readback in EPICS.',
                     optional=False, enforce=str)

    def __init__(self, *args, **kwargs):
        self.system.default = 'diagnostic'
        super().__init__(*args, **kwargs)


class BeamControl(Device):
    """
    Parent class for devices that control any beam parameter.
    """
    def __init__(self, *args, **kwargs):
        self.system.default = 'beam control'
        super().__init__(*args, **kwargs)


class BeamSteering(BeamControl):
    """
    Parent class for devices that direct the beam from one line to another.
    """
    destinations = EntryInfo('Mapping from steering states PV to ' +
                             'destination beamlines',
                             optional=False, enforce=dict)


class ExtraState(Device):
    """
    Parent class for devices that need a single extra states PV because one
    base PV is insufficient to fully define the device.
    """
    states = EntryInfo('Extra state PV, in addition to base.',
                       optional=False, enforce=str)


class ExtraStates(Device):
    """
    Parent class for devices that need multiple extra states PVs because one
    base PV is insufficient to fully define the device.
    """
    states = EntryInfo('Extra states PVs, in addition to base.',
                       optional=False, enforce=list)


# Basic classes that inherit from above
class GateValve(MPS, Vacuum):
    """
    For gate valves, the base pv should be the record one level below the
    state and control PVs. For example, if the open command pv is
    "HXX:MXT:VGC:01:OPN_SW", the base pv is "HXX:MXT:VGC:01".

    A regex will be used to check that "VGC" is found in the base PV.

    The mps pv should be the prefix before the OPN_DI_MPSC segment. For
    example, if the open PV is "HXX:MXT:VGC_01:OPN_DI_MPSC", the base PV would
    be "HXX:MXT:VGC_01". Each of these MPS PVs works slightly differently and
    we'll have to inspect the PV live.
    """
    def __init__(self, *args, **kwargs):
        self.base.enforce = re.compile(r'VGC')
        super().__init__(self, *args, **kwargs)


class Slits(BeamControl):
    """
    For slits, the base PV should be the JAWS record one level below the
    center and width PVs. Note that this is NOT the motor record. For example,
    if the x center PV is "XCS:SB2:DS:JAWS:ACTUAL_XCENTER", then the base PV
    should be "XCS:SB2:DS:JAWS"

    A regex will be used to check that "JAWS" is found in the base PV.
    """
    def __init__(self, *args, **kwargs):
        self.base.enforce = re.compile(r'JAWS')
        super().__init__(self, *args, **kwargs)


class PIM(Diagnostic):
    """
    For profile monitors, the base PV should be the motor states PV that shows
    whether the monitor is out, in at yag, or in at diode. Note that this is
    NOT the motor record. For example, if the command PV to pull the PIM out is
    "XPP:SB3:PIM:OUT:GO", then the base PV is "XPP:SB3:PIM".

    The data PV should be the AreaDetector base. For example, if the image data
    is broadcast on "XCS:SB1:P6740:IMAGE1:ArrayData", the data base should be
    "XCS:SB1:P6740".

    A regex will be used to check that "PIM" is found in the base PV.
    """
    def __init__(self, *args, **kwargs):
        self.base.enforce = re.compile(r'PIM')


class IPM(Diagnostic):
    """
    For intensity monitors, the base PV should be the prefix one level up from
    the diode and target state PVs. Note that this is NOT the motor record, it
    is neither the diode nor the target state PV, and it may not even be a
    valid PV name. For example, if the command PV to set the target position to
    a state is "XPP:SB3:IPM:TARGET:GO" and the command PV to move the diode to
    a state is "XPP:SB3:IPM:DIODE:GO", then the base PV is the shared prefix
    "XPP:SB3:IPM".

    The data PV should be the IPM PV that most reliably predicts beam
    prescence. This will, in general, be the sum of the channels.

    A regex will be used to check that "IPM" is found in the base PV.

    If the diode and target have subtly different recorded z-positions, use the
    diode position for the purposes of this database.
    """
    def __init__(self, *args, **kwargs):
        self.base.enforce = re.compile(r'IPM')


class Attenuator(BeamControl):
    """
    For attunators, the base PV should be the base record from the attentuation
    calculation IOC, one level up from the calculated tranmission ratio. For
    example, if the transmission PV is "XPP:ATT:COM:R_CUR", the base PV is
    "XPP:ATT:COM".

    A regex will be used to check that "ATT" is found in the base PV.
    """
    def __init__(self, *args, **kwargs):
        self.base.enforce = re.compile(r'ATT')


class Stopper(MPS):
    """
    For the stoppers, the base PV should be the combined mps status PV e.g.
    "STPR:XRT1:1:S5IN_MPS".

    The mps PV should be the prefix for the lower mps logic PVs e.g.
    "HFX:UM6:STP_01".
    """
    def __init__(self, *args, **kwargs):
        self.veto.default = True
        super().__init__(self, *args, **kwargs)


class Mirror(BeamSteering, ExtraState):
    """
    For steering mirrors, the base PV should be a states PV that tells us which
    destination the mirror is pointing to. These states should be fairly rough
    and should not be relied on for alignment purposes, except for a guarantee
    that if a state is active, then the beam is not going to some other
    destination: either the state is correct or the beam is missing everything.

    The additional state should be the states PV associated with the mirror's
    in/out.
    """
    pass


class PulsePicker(BeamControl, ExtraState):
    """
    For the pulsepickers, the base PV should be the motor record base that the
    pulsepicker IOC is built on top of e.g. "XCS:SB2:MMS:09".

    The additional state should be the states PV associated with the
    pulsepicker in/out. An example of one such PV is "XCS:SB2:PP:Y".
    """
    pass


class LODCM(BeamSteering, ExtraStates):
    """
    This LODCM class doesn't refer to the full LODCM, but rather one of the two
    crystals. This makes 4 LODCM objects in total, 2 for each LODCM. The base
    PV should be the state PV associated with the h1n or h2n state, depending
    on which crystal we're referring to e.g. "XPP:LODCM:H1N".

    The additional states should be all other available states PVs relating to
    that crystal, or an empty list if no such PVs exist.

    We're simplifying here, assuming the LODCM is aligned and that the states
    are accurate. We'll probably only look at the H1N state for lightpath
    purposes, but it's good to collect all the available information.
    """
    pass
