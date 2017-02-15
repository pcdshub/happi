from .device import Device, EntryInfo

class Slits(Device):
    pass

class PIM(Device):
    pass

class IPM(Device):
    pass

class Attenuator(Device):
    pass

class GateValve(Device):
    mps =  EntryInfo('MPS PV associated with the Valve')
    veto = EntryInfo('Whether MPS considers this valve a veto device',
                     enforce=bool, default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #Create a new default
        self.system = 'vacuum'

class Stopper(Device):
    pass

class Mirror(Device):
    pass

class PulsePicker(Device):
    pass

class LODCM(Device):
    pass
