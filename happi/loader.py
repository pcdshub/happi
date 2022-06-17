"""
Functions to instantiate the Python representations of happi Containers
"""
import asyncio
import importlib
import logging
import sys
import time
import types
from functools import partial
from multiprocessing.pool import ThreadPool
from typing import Any, Callable, Optional

from jinja2 import Environment, meta

from .item import HappiItem
from .utils import create_alias

logger = logging.getLogger(__name__)

cache = dict()
main_event_loop = None


def fill_template(
    template: str,
    item: HappiItem,
    enforce_type: bool = False
) -> Any:
    """
    Fill a Jinja2 template using information from a happi item.

    Parameters
    ----------
    template : str
        Jinja2 template source.

    item : HappiItem
        Any happi item container.

    enforce_type : bool, optional
        Force the output of the rendered template to match the enforced type of
        the happi information that was used to fill it.

    Returns
    -------
    rendered : Any
        string-rendered template if ``enforce_type`` is False, or if happi is
        unable to cast the rendered value to the given type.
    """
    # Create a template and render our happi information inside it
    env = Environment().from_string(template)
    filled = env.render(**item.post())
    # Find which variable we used in the template, get the type and convert our
    # rendered template to agree with this
    info = meta.find_undeclared_variables(env.environment.parse(template))
    if len(info) != 1 or not enforce_type:
        # Enforcing types only works with 1 attribute name in the template
        return filled

    # Get the original attribute back from the item. If this does not exist
    # there is a possibility it is a piece of metadata e.t.c
    attr_name = info.pop()
    try:
        typed_attr = getattr(item, attr_name)
    except AttributeError:
        logger.warning(
            "Can not enforce type to match attribute %s as it does not "
            "exist on the container.", attr_name
        )
        return filled

    # If this was a straight substitution with nothing else in the template we
    # can just return the attribute itself thus preserving type
    if str(typed_attr) == filled:
        return typed_attr

    # If there is something more complex going on we can attempt to convert
    # it to match the type of the original
    attr_type = type(typed_attr)
    try:
        return attr_type(filled)
    except ValueError:
        logger.exception(
            "Unable to convert attribute %s from %r to %s",
            attr_name, filled, attr_type
        )
    return filled


def from_container(
    item: HappiItem,
    attach_md: bool = True,
    use_cache: bool = True,
    threaded: bool = False,
) -> Any:
    """
    Load an object (or "device") from a compatible HappiItem.

    The item container is queried for the ``device_class``, ``args``, and
    ``kwargs``. If the associated Python module is not already loaded it will
    be imported. The specified class is then instantiated with the given args
    and kwargs provided.

    The name ``device`` here refers to what is created after instantiating
    ``device_class``.

    This function does not attempt to catch exceptions either during module
    imports or object creation. If you would like a series of independent
    devices to be loaded use :func:`.load_devices`.

    By default, the instantiated object has the original container added on as
    ``.md``. This allows applications to utilize additional metadata
    information that may not be included in the basic class constructor. On
    later calls, the container you request is checked against this stored
    metadata. If a discrepancy is found the object is **forced** to reload, not
    retrieved from the cache.

    Parameters
    ----------
    item : happi.HappiItem
        The item to load.
    attach_md : bool, optional
        Attach the container to the instantiated object as ``md``.
    use_cache : bool, optional
        When devices are loaded they are stored in the ``happi.cache``
        dictionary. This means that repeated attempts to load the device will
        return the same object. This prevents unnecessary EPICS connections
        from being initialized in the same process. If a new object is
        needed, set ``use_cache`` to `False` and a new object will be created,
        overriding the current cached object. An object with matching name
        and differing metadata will always return a new instantiation of the
        device.
    threaded : bool, optional
        Set this to `True` when calling inside a thread.  This is currently
        unused.

    Returns
    -------
    obj : Any
        This will be of the same type as the return value of the provided
        item's ``device_class``.  As that may be a factory function or a
        class, the exact return type is not guaranteed.
    """

    # Return a cached version of the device if present and not forced
    if use_cache and item.name in cache:
        cached_device = cache[item.name]
        # If the metadata has not been modified or we can't review it.
        # Return the cached object
        if hasattr(cached_device, 'md') and cached_device.md == item:
            logger.debug("Loading %s from cache...", item.name)
            return cached_device

        # Otherwise reload
        logger.warning(
            "Device %s has already been loaded, but the database information "
            "has been modified. Reloading...",
            item.name
        )

    # Find the class and module of the container.
    if not item.device_class:
        raise ValueError(
            f"Item {item.name} does not have an associated Python class"
        )

    cls = import_class(item.device_class)

    # Create correctly typed arguments from happi information
    def create_arg(arg):
        if not isinstance(arg, str):
            return arg
        return fill_template(arg, item, enforce_type=True)

    # Treat all our args and kwargs as templates
    args = [create_arg(arg) for arg in item.args]
    kwargs = dict((key, create_arg(val))
                  for key, val in item.kwargs.items())
    # Return the instantiated item
    obj = cls(*args, **kwargs)
    # Attach the metadata to the object
    if attach_md:
        try:
            setattr(obj, 'md', item)
        except Exception:
            logger.warning("Unable to attach metadata dictionary to device")

    # Store the device in the cache
    cache[item.name] = obj
    return obj


def import_class(device_class: str):
    """
    Interpret a device class import string and extract the class object.

    Parameters
    ----------
    device_class : str
        The module path to find the class e.g.
        ``"pcdsdevices.device_types.IPM"``.

    Returns
    -------
    cls : type or callable
        The class or factory function referred to by the input string.
    """

    mod, cls = device_class.rsplit('.', 1)
    # Import the module if not already present
    # Otherwise use the stashed version in sys.modules
    if mod in sys.modules:
        logger.debug("Using previously imported version of %s", mod)
        mod = sys.modules[mod]
    else:
        logger.debug("Importing %s", mod)
        mod = importlib.import_module(mod)
    # Gather our device class from the given module
    try:
        return getattr(mod, cls)
    except AttributeError as exc:
        raise ImportError("Unable to import %s from %s" %
                          (cls, mod.__name__)) from exc


PostLoad = Callable[[Any], None]


def load_devices(
    *items: HappiItem,
    pprint: bool = False,
    namespace: Optional[object] = None,
    use_cache: bool = True,
    threaded: bool = False,
    post_load: Optional[PostLoad] = None,
    include_load_time: bool = False,
    load_time_threshold: float = 0.5,
    **kwargs
):
    """
    Load a series of devices by way of their HappiItems into a namespace.

    Parameters
    ----------
    *items : HappiItem
        List of happi containers to load.
    pprint: bool, optional
        Print results of device loads.
    namespace : object, optional
        Namespace to collect loaded devices in. By default this will be a
        `types.SimpleNamespace`.
    use_cache : bool, optional
        If set to `False`, we'll ignore the cache and always make new
        devices.
    threaded : bool, optional
        Set to `True` to create each device in a background thread.  Note that
        this assumes that no two devices provided are the same. You are not
        guaranteed to load from the cache correctly if you ask for the same
        device to be loaded twice in the same threaded load.
    post_load : function, optional
        Function of one argument to run on each device after instantiation.
        This could be especially useful during the threaded loading process.
    include_load_time : bool, optional
        Include load time in each message.
    load_time_threshold : float, optional
        Load time above this value, in seconds, will be shown if
        ``include_load_time`` is set.
    kwargs
        Additional keyword arguments passed to :func:`.from_container`.
    """

    # Create our namespace if we were not given one
    namespace = namespace or types.SimpleNamespace()
    name_list = [container.name for container in items]
    if threaded:
        # Pre-import because imports in threads have race conditions
        for item in items:
            try:
                import_class(item.device_class)
            except Exception:
                # Just wait for the normal error handling later
                pass
        global main_event_loop
        if main_event_loop is None:
            main_event_loop = asyncio.get_event_loop()
        pool = ThreadPool(len(items))
        opt_load = partial(
            load_device,
            pprint=pprint,
            use_cache=use_cache,
            threaded=True,
            post_load=post_load,
            include_load_time=include_load_time,
            load_time_threshold=load_time_threshold,
            **kwargs
        )
        loaded_list = pool.map(opt_load, items)
    else:
        loaded_list = []
        for item in items:
            loaded = load_device(
                item,
                pprint=pprint,
                use_cache=use_cache,
                threaded=False,
                post_load=post_load,
                include_load_time=include_load_time,
                load_time_threshold=load_time_threshold,
                **kwargs
            )
            loaded_list.append(loaded)
    for dev, name in zip(loaded_list, name_list):
        attr = create_alias(name)
        setattr(namespace, attr, dev)
    return namespace


def load_device(
    item: HappiItem,
    pprint: bool = False,
    threaded: bool = False,
    post_load: Optional[PostLoad] = None,
    include_load_time: bool = False,
    load_time_threshold: float = 0.5,
    **kwargs
) -> Any:
    """
    Call :func:`.from_container ` and show success/fail.

    Parameters
    ----------
    item : happi.HappiItem
        HappiItem to be loaded.
    pprint: bool, optional
        Print results of the loading status.
    threaded: bool, optional
        Set this to `True` when calling inside a thread.
    post_load : function, optional
        Function of one argument to run on each object after instantiation.
        This could be especially useful during the threaded loading process.
    include_load_time : bool, optional
        Include load time in each message.
    load_time_threshold : float, optional
        Load time above this value, in seconds, will be shown if
        ``include_load_time`` is set.
    kwargs:
        Additional keyword arguments passed to :func:`.from_container`.

    Returns
    -------
    obj : Any
        Returns either the loaded object or the resulting exception from
        trying to load the object.
    """

    logger.debug("Loading device from item %s ...", item.name)

    # We sync with the main thread's loop so that they work as expected later
    if threaded and main_event_loop is not None:
        asyncio.set_event_loop(main_event_loop)

    load_message = f"Loading {item.name} [{item.device_class}] ... "
    success = "\033[32mSUCCESS\033[0m!"
    failed = "\033[31mFAILED\033[0m"

    start_time = time.monotonic()
    if pprint and not threaded:
        print(load_message, end='')

    def get_load_time() -> str:
        """Get the load time information for display."""
        elapsed_time = time.monotonic() - start_time
        if include_load_time and elapsed_time >= load_time_threshold:
            return f" ({elapsed_time:.1f} s)"
        return ""

    def print_load_message(message: str, elapsed: str) -> None:
        if not pprint:
            return

        if threaded:
            print(f"{load_message} {message}{elapsed}")
        else:
            print(f"{message}{elapsed}")

    try:
        obj = from_container(item, **kwargs)
        if post_load is not None:
            post_load(obj)
    except Exception as exc:
        elapsed = get_load_time()
        print_load_message(failed, elapsed)
        logger.exception("Error loading %s%s", item.name, elapsed)
        return exc

    elapsed = get_load_time()
    logger.info("%s %s%s", load_message, success, elapsed)
    print_load_message(success, elapsed)
    return obj
