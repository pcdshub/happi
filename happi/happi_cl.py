"""
Module for a command line interface to happi
"""
# happi_cl.py
# NOTE: Does not work from any environment, must have pcds_conda activated
## Can this script activate/deactivate pcds_conda upon use?

import argparse
import happi.backends.json_db as json_db
import happi.client as client

parser = argparse.ArgumentParser(description='happi command line tool')

# First add search argument
parser.add_argument('--search', action='store_true',
                    help='search for device')
parser.add_argument('--field', help='field in happi database to consider')
parser.add_argument('--value', help="value of 'field' to return results",
                    type=str)

parser.add_argument('--add', action='store_true',
                    help='add a device')
#parser.add_argument('--edit', action='store_true',
#                    help='edit a device')

args = parser.parse_args()
arg_dict = vars(args)

# Instantiate Client and JSONBackend
json_backend = json_db.JSONBackend('/home/sheppard/PCDSGitHub/device_config/db.json')
client = client.Client(json_backend)

if arg_dict['search']:
    if arg_dict['field'] == 'z':
        arg_dict['value'] = float(arg_dict['value'])

    search_args = {arg_dict['field']: arg_dict['value']}

    device = client.find_device(**search_args)
    device.show_info()

if arg_dict['add']:
    dev_info = {}
#    add_args = {}
    print("Enter device information: (press return to default a field "
          "to 'none')")
    # Required arg of client.create_device()
    device_container = input('Device Container: ')

    dev_args = input('args: arg1 arg2 ...] : ')
    if dev_args is not '':
        dev_args_list = dev_args.split(' ')
        dev_info["args"] = dev_args_list
    else:
        dev_info["args"] = ['{{prefix}}']

    beamline = input('beamline: ')
    dev_info["beamline"] = beamline
    
    detailed_screen = input('detailed_screen: ')
    dev_info["detailed_screen"] = detailed_screen

    device_class = input('device_class: ')
    dev_info["device_class"] = device_class
    
    documentation = input('documentation: ')
    dev_info["documentation"] = documentation

    embedded_screen = input('embedded_screen: ')
    dev_info["embedded_screen"] = embedded_screen

    engineering_screen = input('engineering_screen: ')
    dev_info["engineering_screen"] = engineering_screen

    # TODO: Add input for **kwargs
    
    lightpath = bool(input('lightpath: (True/False)'))
    dev_info["lightpath"] = lightpath



    name = input('name: ')
    dev_info["name"] = name

    stand = input('stand: ')
    dev_info["stand"] = stand

    system = input('system: ')
    dev_info["system"] = system

    dev_type = input('type: ')
    dev_info["type"] = dev_type

    z = float(input('Location (z): '))
    dev_info["z"] = z

    new_dev = client.create_device(device_container, **dev_info)
    new_dev.show_info()
    input('Press <Enter> to add device or ^C to cancel\n')

