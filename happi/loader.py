"""
Functions to instantiate the Python representations of happi Containers
"""
############
# Standard #
############
import sys
import logging
import importlib

###############
# Third Party #
###############
from jinja2 import Environment, meta


##########
# Module #
##########

logger = logging.getLogger(__name__)


def fill_template(template, device, enforce_type=False):
    """
    Fill a Jinja2 template using information from a device

    Parameters
    ----------
    template : str
        Jinja2 template

    device : happi.Device
        Any device container

    enforce_type : bool, optional
        Force the output of the rendered template to match the enforced type of
        the happi information that was used to fill it.
    """
    # Create a template and render our happi information inside it
    env = Environment().from_string(template)
    filled = env.render(**device.post())
    if enforce_type:
        # Find which variable we used in the template, get the type and convert
        # our rendered template to agree with this
        info = meta.find_undeclared_variables(env.environment.parse(template))
        enforce = type(getattr(device, info.pop()))
        filled = enforce(filled)
    return filled


def from_container(device):
    """
    Load a device from a happi container

    The container is queried for the device_class, args and kwargs. Then if the
    associated package is not already loaded it is imported. The specified
    class is then instantiated with the given args and kwargs provided.

    Parameters
    ----------
    device : happi.Device

    Returns
    -------
    obj : happi.Device.device_class
    """
    # Find the class and module of the container.
    if not device.device_class:
        raise ValueError("Device %s does not have an associated Python class",
                         device.name)
    mod, cls = device.device_class.rsplit('.', 1)
    # Import the module if not already present
    # Otherwise use the stashed version in sys.modules
    if mod in sys.modules:
        logger.debug("Using previously imported version of %s", mod)
        mod = sys.modules[mod]
    else:
        logger.info("Importing %s", mod)
        mod = importlib.import_module(mod)
    # Gather our device class from the given module
    try:
        cls = getattr(mod, cls)
    except AttributeError as exc:
        raise ImportError("Unable to import %s from %s" %
                          (cls, mod.__name__)) from exc

    # Create correctly typed arguments from happi information
    def create_arg(arg):
        if not isinstance(arg, str):
            return arg
        return fill_template(arg, device, enforce_type=True)

    # Treat all our args and kwargs as templates
    args = [create_arg(arg) for arg in device.args]
    kwargs = dict((key, create_arg(val))
                  for key, val in device.kwargs.items())
    # Return the instantiated device
    return cls(*args, **kwargs)
