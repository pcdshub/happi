.. _convention_label:

Conventions
===========
In order for the database to be as easy to parse as possible we need to
establish conventions on how information is entered. Please read through this
before entering any information into the database.


Basic Device Attributes
-----------------------
These are fields that are common to all device


alias
+++++
This is simply a short name we can use to refer to the device.


base
++++
This should be the base for all of the PVs contained within the device. It does
not matter if this is an invalid record by itself. Each Device Container will
have it's own convention for base PV. See :ref:`Containers`.


beamline
++++++++
Beamline refers to a single segment of the full path with no branching paths.
Paths may only branch between beamlines. As a convention, we are adopting the
following beamline names for the branching paths:

* FEE: from the start of the FEE to M1S.
* SXD: from M1S to M2S
* AMO: from M2S to the AMO IP
* SXR: from M2S to the SXR IP
* HXD: from M1S to XPP LODCM Crystal 1
* XPP: from XPP LODCM Crystal 1 to the XPP IP
* PINK: from XPP LODCM Crystal 1 to XRT-M1
* PERI: from XRT-M1 to XCS LODCM Crystal 2
* XCS: from XCS LODCM Crystal 2 to the XCS IP
* XRT_0: from XRT-M1 to XRT-M2
* XRT_1: from XRT-M2 to XCS LODCM Crystal 1
* XCS_LOM: from XCS LODCM Crystal 1 to Crystal 2
* CXI: from XCS LODCM Crystal 1 to the CXI IP
* MEC: from XRT-M2 to the MEC IP
* MFX: from XRT-M2 to the MFX IP

Mirrors and other steering devices should be the last element of a beamline.
Note that this naming scheme will necessarily have to change for lcls 2.

.. todo::
    
    Drawing for easy beamline assignment in branching

z
++
Position of the device on the z-axis in the lcls coordinates.


stand
+++++
Acronym for the stand the device is associated with, such as DIA or DG1.
Devices with the same stand and beamline can be grouped together.


main_screen
+++++++++++
Path to a control screen for this device.


embedded_screen
+++++++++++++++
Path to an embeddable control screen for this device.


system
++++++
System the device is associated with, e.g. vacuum, timing, etc.


parent
++++++
If this device is a component of another, this should be the alias of the full
device.


Specific Device Attributes
--------------------------
Devices or classes of devices can have additional attributes.


mps
+++
The mps PV associated with an mps device.


veto
++++
A boolean describing whether or not this is a veto device in mps.


data
++++
A PV that gives us readbacks for diagnostic devices.


destinations
++++++++++++
A dict mapping from base PV value to beamline destination for a steering
device, such as a mirror or an LODCM crystal.


states
++++++
An additional PV or multiple additional PVs that represent states records that
are important to the device. This is included when one base PV is not
sufficient.
