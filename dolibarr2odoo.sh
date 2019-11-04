#!/bin/bash

#set -x

#-------------------
# test args

if [ "${1}" = "" ]; then
        echo
        echo "USAGE: ${0} <configfile>"
        echo
        exit -1
fi

source ${1}

ADDONS_DIR=${addons_directory}

export PYTHONPATH=${PYTHONPATH}:${ADDONS_DIR}/doli2odoo/:${ADDONS_DIR}/odootools

python3 ${ADDONS_DIR}/doli2odoo/scripts/dolibarr2odoo.py -c ${1}
