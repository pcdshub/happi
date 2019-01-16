"""
Module for a command line interface to happi
"""
# cli.py
# NOTE: Does not work from any environment, must have pcds_conda activated
## Can this script activate/deactivate pcds_conda upon use?

import argparse
import sys
import happi.backends.json_db as json_db
import happi.client as hcl

parser = argparse.ArgumentParser(description='happi command line tool')

# First add search argument
parser.add_argument('--search', action='store_true',
                    help='search for device')
parser.add_argument('--field', help='field in happi database to consider')
parser.add_argument('--value', help="value of 'field' to return results",
                    type=str)

parser.add_argument('--add', action='store_true',
                    help='add a device')

# TODO: Implement edit option
#parser.add_argument('--edit', action='store_true',
#                    help='edit a device')

#args = parser.parse_args()
#arg_dict = vars(args)

def happi_cli(args):
    args = parser.parse_args(args)
    print(args)
    arg_dict = vars(args)
    print(arg_dict)
    # Instantiate Client and JSONBackend
    json_backend = json_db.JSONBackend('/home/sheppard/PCDSGitHub/device_config/db.json')
    client = hcl.Client(json_backend)

    if arg_dict['search']:
        if arg_dict['field'] == 'z':
            arg_dict['value'] = float(arg_dict['value'])

        search_args = {arg_dict['field']: arg_dict['value']}

        device = client.find_device(**search_args)
        device.show_info()

    if arg_dict['add']:
        dev_info = {}
        
        all_fields = ["beamline", "detailed_screen", "device_class",
                      "documentation", "embedded_screen",
                      "engineering_screen", "lightpath", "macros", "name",
                      "parent", "prefix", "stand", "system", "type", "z"]

        print("Enter device information: (press <return> to default a" 
               "field to 'none')")
        # Required arg of client.create_device()
        device_container = input('Device Container (required): ')

        ###################################################################
        # TODO: Need better way to input args and kwargs
        dev_args = input('args: arg1 arg2 ...: ')
        if dev_args is not '':
            dev_args_list = dev_args.split(' ')
            dev_info["args"] = dev_args_list
        else:
            dev_info["args"] = ['{{prefix}}']

        dev_kwargs = input("kwargs: 'kwarg1': 'default1' 'kwarg2': 'default2', ... : ")
        if dev_kwargs is not '':
            dev_kwargs_list = dev_kwargs.split(' ')
            dev_kwargs_dict = {}
            for i in range(0, len(dev_kwargs_list), 2):
                key_str = dev_kwargs_list[i]
                key = key_str[0:len(key_str) - 1]
                dev_kwargs_dict[key] = dev_kwargs_list[i + 1]
            dev_info["kwargs"] = dev_kwargs_dict
        ###################################################################

        ###################################################################
        # Fields with non-string values
        for field in all_fields:
            value = input(field + ': ')
            if field is "lightpath":
                value = bool(value)
            elif field is "z":
                value = float(value)
            dev_info[field] = value
        ###################################################################

        all_keys = list(dev_info.keys())

        for key in all_keys:
            if dev_info[key] == '':
                del dev_info[key]

        new_dev = client.create_device(device_container, **dev_info)
        new_dev.show_info()
        input('Press <Enter> to add device or ^C to cancel\n')
        client.add_device(new_dev)

def main():
    """Execute the ``happi_cli`` with command line arguments"""
    happi_cli(sys.argv[1:])

if __name__ == '__main__':
    main()
