#!/bin/bash

#
# Usage:
#   RAL_dbdump.sh <config.yaml> <dbconfig.cfg> <RSE> <scratch dir> <output dir>
#

config_file=$1
rucio_config_file=$2
RSE=$3
scratch=$4
out=$5

export PYTHONPATH=`pwd`/cmp3:`pwd`


today=`date -u +%Y_%m_%d_00_00`

b_prefix=${scratch}/${RSE}_${today}_B.list
stats=${out}/${RSE}_${today}_stats.json
    
echo
echo DB dump before ...
echo

rucio_cfg=""
if [ "$rucio_config_file" != "-" ]; then
    rucio_cfg="-d $rucio_config_file"
fi

rm -rf ${b_prefix}*
python3 cmp3/db_dump.py -o ${b_prefix} -c ${config_file} $rucio_cfg -s ${stats} -S "dbdump_before" ${RSE} 

exit=$?
if [ "$exit" != "0" ]; then
    rm -rf ${b_prefix}*
    exit $exit
fi


