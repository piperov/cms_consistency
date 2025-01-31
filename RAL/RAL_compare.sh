#!/bin/bash


#
# Usage:
#   RAL_compare.sh <config.yaml> <dbconfig.cfg> <RSE> <scratch dir> <output dir> [<cert file> [<key file>]]
#

config=$1
rucio_config_file=$2
RSE=$3
scratch=$4
out=$5
cert=$6
key=$7

server=ceph-gw1.gridpp.rl.ac.uk

case $RSE in
	T1_UK_RAL_Tape)
		dump_path="/store/accounting/tape"
		;;
	T1_UK_RAL_Disk)
		dump_path="/store/accounting"
		;;
	*)
		echo Unknown RSE $RSE
		exit 1
		;;
esac
	
export PYTHONPATH=`pwd`/cmp3:`pwd`


sleep_interval=1000      # 10 minutes
attempts="1 2 3 4 5 6"


today=`date -u +%Y_%m_%d_00_00`

b_prefix=${scratch}/${RSE}_${today}_B.list
a_prefix=${scratch}/${RSE}_${today}_A.list
r_prefix=${scratch}/${RSE}_${today}_R.list
stats=${out}/${RSE}_${today}_stats.json

d_out=${out}/${RSE}_${today}_D.list
m_out=${out}/${RSE}_${today}_M.list

tape_dump_tmp=${scratch}/${RSE}_${today}_tape_dump.gz

# X509 proxy
if [ "$cert" != "" ]; then
        if [ "$key" == "" ]; then
            export X509_USER_PROXY=$cert
        else
            voms-proxy-init -voms cms -rfc -valid 192:00 --cert $cert --key $key
        fi
fi

echo
echo Downloading tape dump ...
echo

downloaded="no"

for attempt in $attempts; do
    echo Attempt $attempt ...
    rm -f ${tape_dump_tmp}
	timestamp=`date -u +%Y%m%d`
	t0=`date +%s`
	dump_file=${dump_path}/dump_${timestamp}.gz
	dump_url=root://${server}/cms:${dump_file}
    xrdcp ${dump_url} ${tape_dump_tmp}
    if [ "$?" != "0" ] || [ ! -f ${tape_dump_tmp} ]; then
	    rm -f ${tape_dump_tmp}
        echo sleeping ...
        sleep $sleep_interval
    else
        echo succeeded
        python3 cmp3/partition.py -c $config -r $RSE -q -o ${r_prefix} ${tape_dump_tmp}
		t1=`date +%s`
	    rm -f ${tape_dump_tmp}
        downloaded="yes"

		# count files in the dump
		n=`wc -l ${r_prefix}.* | egrep  '^[ ]*[0-9]+[ ]+total' | awk -e '{ print $1 }'`
		n=${n:-0}
		
		python3 cmp3/stats.py -k scanner ${stats} <<_EOF_
		    {
		        "rse":"$RSE",
		        "scanner":{
		            "type":"site_dump",
					"url":"${dump_url}",
		            "version":null
		        },
		        "server":"${server}",
		        "start_time":$t0,
		        "end_time":$t1,
		        "status":   "done",
				"total_files":$n
		    }
_EOF_

        break
    fi
done

if [ "$downloaded" == "no" ]; then
    exit 1
fi

rucio_cfg=""
if [ "$rucio_config_file" != "-" ]; then
    rucio_cfg="-d $rucio_config_file"
fi

echo
echo DB dump after ...
echo

python3 cmp3/db_dump.py -o ${a_prefix} -c ${config} $rucio_cfg -s ${stats} -S "dbdump_after" ${RSE} 
                
echo
echo Comparing ...
echo

python3 cmp3/cmp3.py -s ${stats} ${b_prefix} ${r_prefix} ${a_prefix} ${d_out} ${m_out}

echo Dark list:    `wc -l ${d_out}`
echo Missing list: `wc -l ${m_out}`

    

