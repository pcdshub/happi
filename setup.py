import versioneer
from setuptools import (setup, find_packages)

setup(name     = 'happi',
      version  = versioneer.get_version(),
      cmdclass = versioneer.get_cmdclass(),
      license  = 'BSD',
      author   = 'SLAC National Accelerator Laboratory',

      packages    = find_packages(),
      description = 'Happi Database Access for LCLS Beamline Devices',

    )
