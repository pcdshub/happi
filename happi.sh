#!/bin/bash
# happi.sh
# Command line tool to search, add, or edit entries in happi db.json file

usage()
{
cat << EOF
usage: $0 options

command line tool to parse/edit the happi database

OPTIONS:
-h display this help screen
-s search database for entry
-e edit existing entry in database
-a add new entry to database
EOF
}

# Note: $1 = argument given at command line
# Note2: Need to have a conda environment activated, could do in script?
search()
{
#python -c "import happi.client.Client; client = Client(); client.find_device('$1')"
#PYTHON_CODE=$(cat <<END
#import math
#for i in range($1):
#    print(i**2)
#    print($2)
#END
#) # example python code in bash script
PYTHON_CODE=$(cat <<END
import happi.backends.json_db as json_db
import happi.client as client
json_backend = json_db.JSONBackend('/home/sheppard/PCDSGitHub/device_config/db.json')
client_obj = client.Client(json_backend)
search_result = client_obj.find_device($1='$2')
search_result.show_info()
END
)

RESULT="$(python -c "$PYTHON_CODE")"
echo "$RESULT"
}

while getopts "s:e:a:h" OPTION
do
    case $OPTION in
        h)
            usage
            exit 1
            ;;
        s)
            search $OPTARG
            # For now assume two arguments passed of form
            # "field_in_dict desired_value_for_field"
            # i.e:
            # ./happi.sh -s "prefix CXI:DG1:JAWS"
            exit 1
            ;;
        e)
            # edit existing entry in database
            exit 1
            ;;
        a)
            # Add new entry to database
            exit 1
            ;;
        esac
done
