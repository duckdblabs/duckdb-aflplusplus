#!/bin/bash

# this script reproduces the errors found by: duckdb_file_fuzzer

COUNTER=0
ERROR_COUNTER=0
CRASH_COUNTER=0

mkdir -p ../report
mkdir -p tmp
mkdir -p fixed_checksum_internal_error_files
mkdir -p fixed_checksum_crash_files
mkdir -p report
for fuzz_result in ../fuzz_results/duckdb_file_fuzzer/default/crashes/*;
do
    cp $fuzz_result ./tmp/file_$COUNTER
    python3 ./fix_duckdb_file.py ./tmp/file_$COUNTER
    duckdb -c "ATTACH './tmp/file_$COUNTER' AS tmp_db (READ_ONLY); use tmp_db; show tables;" > /dev/null
    exit_status=$?
    if [ "$exit_status" -ne "0" ]; then
        echo "error in file_$COUNTER, exit status: $exit_status"
        if [ "$exit_status" -eq "1" ]; then
            cp $COUNTER report
            ((ERROR_COUNTER+=1))
            cp ./tmp/file_$COUNTER fixed_checksum_internal_error_files
        else
            ((CRASH_COUNTER+=1))
            cp ./tmp/file_$COUNTER fixed_checksum_crash_files
        fi
    fi
    ((COUNTER+=1))
done

mv tmp ../report
mv fixed_checksum_internal_error_files ../report
mv fixed_checksum_crash_files ../report

echo "$COUNTER duckdb files have been read, nr of graceful errors: '$ERROR_COUNTER', nr of crashes: $CRASH_COUNTER"
