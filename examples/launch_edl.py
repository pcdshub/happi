import argparse
import logging
import os
import subprocess
from distutils.spawn import find_executable

from jinja2 import Environment

import happi

logger = logging.getLogger(__name__)

description = """\
Launch the EDL screen for a Happi device based on the information contained
within the database

Example:
    %(prog)s XRT_M2  --embedded

This launches the embedded EDL screen for the device contained within the Happi
database with the name 'XRT_M2'
"""


def launch(path, wait=True, wd=None, macros=None):
    """
    Launch an EDL file

    Parameters
    ----------
    path : str
        Path to file

    wd : str, optional
        Working directory to launch screen, otherwise the current directory
        is used

    wait : bool, optional
        Block the main thread while the EDM preview is open

    macros : str, optional
        String of macro substitutions

    Returns
    -------
    proc : ``subprocess.Popen``
        Process containing EDM launch

    Raises
    ------
    FileNotFoundError:
        If the .edl file does not exist

    OSError:
        If the ``edm`` executable is not in the system path

     Example
    -------
    .. code::

        edm_proc = launch('path/to/my.edl', MACRO='TST:MACRO')
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    edm_args = ['edm', '-x', '-eolc']

    if macros:
        edm_args.extend(['-m', macros])

    edm_args.append(path)

    try:
        print("Launching {} with the following arguments {} ..."
              "".format(path, edm_args))
        proc = subprocess.Popen(edm_args, cwd=wd, stdout=None)

        if wait:
            proc.wait()

    except OSError:
        if not find_executable('edm'):
            raise OSError('EDM is not in current environment')

        raise

    except KeyboardInterrupt:
        print('Aborted via KeyboardInterrupt ...')
        proc.terminate()

    return proc


def main():
    # Parse command line
    fclass = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(epilog=description,
                                     formatter_class=fclass)

    # Arguments
    parser.add_argument('name', help='Name of Device')

    parser.add_argument('-e', '--embedded', dest='embedded',
                        help='Choice to use embedded screen',
                        default=False, action='store_true')

    parser.add_argument('-b', '--block', dest='block',
                        help='Block the main thread while '
                             'the screen is open',
                        default=False, action='store_true')

    parser.add_argument('-d', '--dir', dest='dir',
                        help='Directory to launch screen from',
                        default=None)

    # Parse arguments
    args = parser.parse_args()
    client = happi.Client()

    try:
        device = client.load_device(name=args.name)

    except happi.errors.SearchError:
        print('Unable to locate any device with '
              'name {} in the database.'
              ''.format(args.name))
        return

    # Create string of macros based on template
    env = Environment().from_string(device.macros)
    macros = env.render(**device.post())

    # Gather screen path
    if args.embedded:
        screen = device.embedded_screen
    else:
        screen = device.main_screen

    # Launch screen
    launch(screen, wait=args.block, wd=args.dir, macros=macros)


if __name__ == '__main__':
    main()
