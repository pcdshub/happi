"""
Define subclasses of Device for specific hardware.
"""
import re
from copy import copy, deepcopy
from .device import Device, EntryInfo


class Vacuum(Device):
    """
    Parent class for devices in the vacuum system.
    """
    system = copy(Device.system)
    system.default = 'vacuum'


class Diagnostic(Device):
    """
    Parent class for devices that are used as diagnostics.
    """
    system = copy(Device.system)
    system.default = 'diagnostic'
    data = EntryInfo('PV that gives us the diagnostic readback in EPICS.',
                     enforce=str)


class BeamControl(Device):
    """
    Parent class for devices that control any beam parameter.
    """
    system = copy(Device.system)
    system.default = 'beam control'


# Basic classes that inherit from above
class GateValve(Vacuum):
    """
    Standard isolation valves. Generally, these close when there is a
    problem and beam is not allowed. Devices made with this class will be set
    as part of the vacuum system.

    Attributes
    ----------
    prefix : str
        The prefix pv should be the record one level below the state and
        control PVs. For example, if the open command pv is
        "HXX:MXT:VGC:01:OPN_SW", the base pv is "HXX:MXT:VGC:01". A regex will
        be used to check that "VGC" is found in the base PV.

    veto : bool
        Set this to True if the gate valve is a veto device.
    """
    prefix = copy(Vacuum.prefix)
    prefix.enforce = re.compile(r'.*VGC.*')
    device_class = copy(Device.device_class)
    device_class.default = 'pcdsdevices.device_types.GateValve'


class Slits(BeamControl):
    """
    Mechanical devices to control beam profile. This class refers specifically
    to slits that use the JAWS record. These devices will be assigned the beam
    control system by default.

    Attributes
    ----------
    prefix : str
        The prefix PV should be the JAWS record one level below the center and
        width PVs. Note that this is NOT the motor record. For example, if the
        x center PV is "XCS:SB2:DS:JAWS:ACTUAL_XCENTER", then the base PV
        should be "XCS:SB2:DS:JAWS". A regex will be used to check that "JAWS"
        is found in the base PV.
    """
    prefix = copy(BeamControl.prefix)
    prefix.enforce = re.compile(r'.*JAWS.*')
    device_class = copy(Device.device_class)
    device_class.default = 'pcdsdevices.device_types.Slits'


class PIM(Diagnostic):
    """
    Beam profile monitors. All of these are cameras pointing at YAG screens.
    These devices have a data attribute in addition to the standard entries to
    link up the device with its camera output. These devices will be assigned
    the diagnostic system by default.

    Attributes
    ----------
    prefix : str
        The base PV should be the motor states PV that shows whether the
        monitor is out, in at yag, or in at diode. Note that this is NOT the
        motor record. For example, if the command PV to pull the PIM out is
        "XPP:SB3:PIM:OUT:GO", then the base PV is "XPP:SB3:PIM". A regex will
        be used to check that "PIM" is found in the base PV.

    data : str
        The data PV should be the AreaDetector base. For example, if the image
        data is broadcast on "XCS:SB1:P6740:IMAGE1:ArrayData", the data base
        should be "XCS:SB1:P6740".
    """
    prefix = copy(Diagnostic.prefix)
    prefix.enforce = re.compile(r'.*PIM.*')
    prefix_det = EntryInfo("Prefix for associated camera", enforce=str)
    device_class = copy(Device.device_class)
    device_class.default = 'pcdsdevices.device_types.PIM'
    kwargs = deepcopy(Device.kwargs)
    kwargs.default['prefix_det'] = "{{prefix_det}}"


class IPM(Diagnostic):
    """
    Beam intensity monitors. These are often used as a sanity check for beam
    presence, though they can also be used to track shot to shot intensity and
    estimate beam position. These devices have a data attribute in addition to
    the standard entries to link the device with its scalar output. These
    devices will be assigned the diagnostic system by default.

    Attributes
    ----------
    prefix : str
        The base PV should be the prefix one level up from the diode and target
        state PVs. Note that this is NOT the motor record, it is neither the
        diode nor the target state PV, and it may not even be a valid PV name.
        For example, if the command PV to set the target position to a state is
        "XPP:SB3:IPM:TARGET:GO" and the command PV to move the diode to a state
        is "XPP:SB3:IPM:DIODE:GO", then the base PV is the shared prefix
        "XPP:SB3:IPM". A regex will be used to check that "IPM" is found in the
        base PV.

    data : str
        The data PV should be the IPM PV that most reliably predicts beam
        prescence. This will, in general, be the sum of the channels.

    z : float
        If the diode and target have subtly different recorded z-positions, use
        the diode position for the purposes of this database.
    """
    prefix = copy(Diagnostic.prefix)
    prefix.enforce = re.compile(r'.*IPM.*')
    device_class = copy(Device.device_class)
    device_class.default = 'pcdsdevices.device_types.IPM'


class Attenuator(BeamControl):
    """
    Beam attenuators, used to get a lower intensity beam downstream to protect
    the sample or to protect hardware components. These devices will be
    assigned the beam control system by default.

    Attributes
    ----------
    prefix : str
        For attunators, the base PV should be the base record from the
        attentuation calculation and control IOC, one level up from the
        calculated tranmission ratio. For example, if the transmission PV is
        "XPP:ATT:COM:R_CUR", the base PV is "XPP:ATT". A regex will be used
        to check that "ATT" is found in the base PV

    n_filters : int
        Number of Attenuator blades
    """
    prefix = copy(BeamControl.prefix)
    prefix.enforce = re.compile(r'.*ATT.*')
    device_class = copy(Device.device_class)
    device_class.default = 'pcdsdevices.device_types.Attenuator'
    n_filters = EntryInfo("Number of filters on the Attenuator",
                          enforce=int, optional=False)
    kwargs = deepcopy(Device.kwargs)
    kwargs.default['n_filters'] = "{{n_filters}}"


class Stopper(Device):
    """
    Large devices that prevent beam when it could cause damage to hardware.

    Attributes
    ----------
    prefix : str
        The base PV should be the combined mps status PV e.g.
        "STPR:XRT1:1:S5IN_MPS".
    """
    device_class = copy(Device.device_class)
    device_class = 'pcdsdevices.device_types.Stopper'


class OffsetMirror(BeamControl):
    """
    A device that steers beam in the x direction by changing a pitch motor.
    These are used for beam delivery and alignment. These have additional
    entires for destinations and in/out state. Mirrors will have their system
    set to beam control by default.

    Attributes
    ----------
    prefix : str
        The base PV should be a states PV that tells us which destination the
        mirror is pointing to. These states will be fairly rough and should not
        be relied on for alignment purposes, except for a guarantee that if a
        state is not active, then the beam is definitely not pointing to that
        state.
        If the mirror is purely for alignment and not for steering, or it
        doesn't make sense for the pitch to have states, this can be the pitch
        control motor record base instead.

    prefix_xy : str, optional
        Name of the X and Y motors if different than the standard prefix

    xgantry_prefix : str, optional
        Prefix of the X Gantry PVs if different than the standard prefix
    """
    device_class = copy(Device.device_class)
    device_class.default = 'pcdsdevices.device_types.OffsetMirror'
    prefix_xy = EntryInfo("Prefix for X and Y motors", enforce=str)
    xgantry_prefix = EntryInfo("Prefix for the X Gantry", enforce=str)


class PulsePicker(BeamControl):
    """
    A device that syncs with the timing system to control when beam arrives in
    the hutch. These have an additional states entry to define their in/out
    states pv. Pulse pickers will be assigned the beam control system by
    default.

    Attributes
    ----------
    prefix : str
        The base PV should be the motor record base that the pulsepicker IOC
        is built on top of e.g. "XCS:SB2:MMS:09".

    states : str
        The additional state should be the states PV associated with the
        pulsepicker in/out. An example of one such PV is "XCS:SB2:PP:Y".
    """
    device_class = copy(Device.device_class)
    device_class.default = 'pcdsdevices.device_types.PulsePicker'


class LODCM(BeamControl):
    """
    This LODCM class doesn't refer to the full LODCM, but rather one of the two
    crystals. This makes 4 LODCM objects in total, 2 for each LODCM. These have
    an additional states entry to define a list of all the miscellaneous states
    pvs associated with the LODCMs. LODCMs will be assigned the beam control
    system by default.

    We're simplifying here, assuming the LODCM is aligned and that the states
    are accurate. We'll probably only look at the H1N state for lightpath
    purposes, but it's good to collect all the available information.

    Attributes
    ----------
    prefix : str
        The base PV should be the state PV associated with the h1n or h2n
        state, depending on which crystal we're referring to e.g.
        "XPP:LODCM:H1N".

    mono_line : str
        Name of the mono line
    """
    device_class = copy(Device.device_class)
    device_class.default = 'pcdsdevices.device_types.LODCM'
    mono_line = EntryInfo("Name of the MONO beamline",
                          enforce=str, optional=False)
    kwargs = deepcopy(Device.kwargs)
    kwargs.default.update({'mono_line': '{{mono_line}}',
                           'main_line': '{{beamline}}'})


class MovableStand(Device):
    """
    This class stores information about stands that move, like XPP's hand-crank
    that moves SB2 and SB3 from the PINK to XPP lines and back. There is no
    need to instantiate one of these for static stands.

    Attributes
    ----------
    prefix : str
        If there is a single PV with the stand's location, this should be the
        base PV. In general, these devices will actually have multiple PVs
        with binary outputs that have yes/no on the stand being in each
        position. In these cases we pick the common prefix of these PVs.

    stand : list
        List of stands affected by table movement.
    """
    stand = copy(Device.stand)
    stand.enforce = list
    system = copy(Device.system)
    system.default = 'changeover'


class Motor(Device):
    """
    A Generic EpicsMotor
    """
    device_class = copy(Device.device_class)
    device_class.default = 'pcdsdevices.device_types.Motor'
    system = copy(Device.system)
    system.default = 'motion'


class AreaDetector(Device):
    """
    A Generic EpicsCamera
    """
    device_class = copy(Device.device_class)
    device_class.default = 'pcdsdevices.device_types.PCDSDetector'
    system = copy(Device.system)
    system.default = 'camera'


class Acromag(Device):
    """
    A Generic class for Acromag
    """
    device_class = copy(Device.device_class)
    device_class.default = 'pcdsdevices.device_types.Acromag'
    system = copy(Device.system)
    system.default = 'acromag'


class Trigger(Device):
    """
    A Generic class for Controls Triggers
    """
    device_class = copy(Device.device_class)
    device_class.default = 'pcdsdevices.device_types.Trigger'
    system = copy(Device.system)
    system.default = 'timing'
