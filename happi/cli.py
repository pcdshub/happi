"""
Module for a command line interface to happi
"""
# cli.py

import os
import argparse
import sys
import happi.client as hcl
import logging
import coloredlogs

logger = logging.getLogger(__name__)

# Argument Parser Setup
parser = argparse.ArgumentParser(description='happi command line tool')

# First add search argument
parser.add_argument('--search', action='store_true',
                    help='search for device')
parser.add_argument('--search_args', nargs=argparse.REMAINDER,
                    help='search criteria: [--search_args] field value')
parser.add_argument('--verbose', '-v', action='store_true',
                    help='Show the degub logging stream')
parser.add_argument('--version', '-V', action='store_true',
                    help='Current version and location '
                    'of Happi installation.')

# TODO: Implement add and edit options
# parser.add_argument('--add', action='store_true', # needs work
#                    help='add a device')
# parser.add_argument('--edit', action='store_true',
#                    help='edit a device')


def happi_cli(args):
    args = parser.parse_args(args)

    # Logging Level handling
    if args.verbose:
        level = "DEBUG"
        shown_logger = logging.getLogger('happi')
    else:
        shown_logger = logging.getLogger()
        level = "INFO"
    coloredlogs.install(level=level, logger=shown_logger,
                        fmt='[%(asctime)s] - %(levelname)s -  %(message)s')
    logger.debug("Set logging level of %r to %r", shown_logger.name, level)

    # Version endpoint
    if args.version:
        print(f'Happi: Version {happi.__version__} from {happi.__file__}')
        return
    logger.debug('Command line arguments: %r' % args)

    xdg_cfg = os.environ.get("XDG_CONFIG_HOME", '')
    happi_cfg = os.environ.get("HAPPI_CFG", '')
    os.environ['XDG_CONFIG_HOME'] = os.getcwd()
    os.environ['HAPPI_CFG'] = ''

    cfg_path = hcl.Client.find_config()

    os.environ["HAPPI_CFG"] = happi_cfg
    os.environ["XDG_CONFIG_HOME"] = xdg_cfg
    client = hcl.Client.from_config(cfg=cfg_path)

    if args.search:
        if args.search_args[0] is 'z':
            args.search_args[1] = float(args.search_args[1])
        search_args = {args.search_args[0]: args.search_args[1]}

        device = client.find_device(**search_args)
        device.show_info()

#    if args.add:
#        dev_info = {}
#
#        all_fields = ["beamline", "detailed_screen", "device_class",
#                      "documentation", "embedded_screen",
#                      "engineering_screen", "lightpath", "macros", "name",
#                      "parent", "prefix", "stand", "system", "type", "z"]
#
#        print("Enter device information: (press <return> to default a "
#               "field to 'none')")
#        # Required arg of client.create_device()
#        device_container = input('Device Container (required): ')
#
#        ###################################################################
#        # TODO: Need better way to input args and kwargs
#        dev_args = input('args: arg1 arg2 ...: ')
#        if dev_args is not '':
#            dev_args_list = dev_args.split(' ')
#            dev_info["args"] = dev_args_list
#        else:
#            dev_info["args"] = ['{{prefix}}']
#
#        dev_kwargs = input("kwargs: 'kwarg1': 'default1' 'kwarg2': 'default2', ... : ")
#        if dev_kwargs is not '':
#            dev_kwargs_list = dev_kwargs.split(' ')
#            dev_kwargs_dict = {}
#            for i in range(0, len(dev_kwargs_list), 2):
#                key_str = dev_kwargs_list[i]
#                key = key_str[0:len(key_str) - 1]
#                dev_kwargs_dict[key] = dev_kwargs_list[i + 1]
#            dev_info["kwargs"] = dev_kwargs_dict
#        ###################################################################
#
#        ###################################################################
#        # Fields with non-string values
#        for field in all_fields:
#            value = input(field + ': ')
#            if field is "lightpath":
#                value = bool(value)
#            elif field is "z":
#                value = float(value)
#            dev_info[field] = value
#        ###################################################################
#
#        all_keys = list(dev_info.keys())
#
#        for key in all_keys:
#            if dev_info[key] == '':
#                del dev_info[key]
#
#        new_dev = client.create_device(device_container, **dev_info)
#        new_dev.show_info()
#        input('Press <Enter> to add device or ^C to cancel\n')
#        client.add_device(new_dev)


def main():
    """Execute the ``happi_cli`` with command line arguments"""
    happi_cli(sys.argv[1:])

# if __name__ == '__main__':
#     main()
