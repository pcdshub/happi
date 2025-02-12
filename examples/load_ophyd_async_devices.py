from bluesky.run_engine import RunEngine
import happi
import happi.loader
from IPython import get_ipython
from types import SimpleNamespace
from bluesky.plans import count, scan
from ophyd_async.plan_stubs import ensure_connected

ip = get_ipython()

client = happi.Client(path="ophyd_async_db.json")

from ophyd_async.core import init_devices

print("Initializing bluesky RunEngine...")
RE = RunEngine({})

init_ns = SimpleNamespace()

print("Instantiating all helper objects...")
happi.loader.load_devices(
    *[result.item for result in client.search(type="HappiItem")],
    pprint=True,
    include_load_time=True,
    namespace=init_ns,
)

print("Initializing Ophyd Async devices...")
happi.loader.load_devices(
    *[result.item for result in client.search(type="OphydAsyncItem")],
    pprint=True,
    include_load_time=True,
    post_load=lambda device: RE(ensure_connected(device)),
    namespace=init_ns,
)

ip.user_ns.update(vars(init_ns))
print("Done.")