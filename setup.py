import versioneer
from setuptools import (setup, find_packages)

with open('requirements.txt') as f:
    requirements = f.read().split()

git_requirements = [r for r in requirements if r.startswith('git+')]
requirements = [r for r in requirements if not r.startswith('git+')]
if len(requirements) > 0:
    print("User must install the following packages manually:\n" +
            "\n".join(f' {r}' for r in git_requirements))

setup(name='happi',
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      author='SLAC National Accelerator Laboratory',
      packages=find_packages(),
      include_package_data=True,
      install_requires=requirements,
      description='Happi Database Access for LCLS Beamline Devices',
      entry_points={'console_scripts': ['happi=happi.cli:main']})
