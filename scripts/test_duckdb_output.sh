#!/bin/bash

# this script reproduces the errors found by: duckdb_file_fuzzer

COUNTER=0
ERROR_COUNTER=0
CRASH_COUNTER=0

mkdir -p tmp
for fuzz_result in ../fuzz_results/duckdb_file_fuzzer/default/crashes/*;
do
    cp $fuzz_result ./tmp/file_$COUNTER
    python3 ./fix_filesize_header_checksums.py ./tmp/file_$COUNTER
    duckdb -c "ATTACH './tmp/file_$COUNTER' AS tmp_db (READ_ONLY); use tmp_db; show tables;" > /dev/null
    exit_status=$?
    if [ "$exit_status" -ne "0" ]; then
        echo "error in file_$COUNTER, exit status: $exit_status"
        if [ "$exit_status" -eq "1" ]; then
            ((ERROR_COUNTER+=1))
        else
            ((CRASH_COUNTER+=1))
        fi
    fi
    ((COUNTER+=1))
done
echo "$COUNTER duckdb files have been read, nr of graceful errors: '$ERROR_COUNTER', nr of crashes: $CRASH_COUNTER"
rm -rf ./tmp/
