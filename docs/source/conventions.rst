.. _convention_label:

Conventions
===========
In order for the database to be as easy to parse as possible we need to
establish conventions on how information is entered. Please read through this
before entering any information into the database.


Basic Device Attributes
-----------------------
These are fields that are common to all device


name
+++++
This is simply a short name we can use to refer to the device.


prefix
++++++
This should be the prefix for all of the PVs contained within the device. It does
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

macros
++++++
Most screens will require a set of macros to be provided at launch time. In
order to prevent information being duplicated in this macro string and other
EntryInfo, this can be given as a ``jinja2`` template. This may sound
intimidating, but in practice it is very simple. Let us look at an example for
a basic camera, who has a nice EDL screen that takes a ``CAM`` and
an ``EVR`` macro substitution. Now every time we change the EVR trigger for
this camera, we want to make sure we only need to change this in one place, so
lets make a template that pulls the information from the Container itself. The
below example creates a new container, adds a new macro templates then
performs a quick test.

The main thing to note is the use of keywords found within the repeated
brackets. When this string is loaded as a ``Template``, we can easily
substitute our EntryInfo in place of these brackets.

.. ipython:: python 

    import happi

    #Create a new container
    class Camera(happi.Device):
        evr = happi.EntryInfo('EVR Trigger for Camera')

    #Instantiate
    cam = Camera(name='Opal', prefix='BASE:CAM:PV',
                 beamline='TST', evr='EVR:TRIG:PV')

    #Link our EDL screens 
    cam.main_screen = 'my_screens/camera.edl'

    #Add our macros template
    cam.macros = 'CAM={{prefix}}, EVR={{evr}}'

That is all the neccesary information you need to provide, other scripts that
utilize the information will do something similar to the script below to
substitute device information into our template

.. ipython:: python
    
    from jinja2 import Environment

    #Create new template
    env = Environment().from_string(cam.macros)

    #Render our template given the device information
    env.render(prefix=cam.prefix, evr=cam.evr)

A succinct script exists in the ``examples`` section of the module that
substitutes and launches the associated EDM screen provided the device name.

system
++++++
System the device is associated with, e.g. vacuum, timing, etc.


parent
++++++
If this device is a component of another, this should be the name of the full
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
are important to the device. This is included when one prefix PV is not
sufficient.
