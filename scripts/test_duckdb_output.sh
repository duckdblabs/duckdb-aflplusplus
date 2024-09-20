#!/bin/bash

# this script reproduces the errors found by: duckdb_file_fuzzer

COUNTER=0
ERROR_COUNTER=0

mkdir -p tmp
for fuzz_result in ../fuzz_results/duckdb_file_fuzzer/default/queue/*;
do
    cp $fuzz_result ./tmp/file_$COUNTER
    python3 ./fix_filesize_header_checksums.py ./tmp/file_$COUNTER
    duckdb -c "ATTACH './tmp/file_$COUNTER' AS tmp_db (READ_ONLY); use tmp_db; show tables;" > /dev/null
    if [ "$?" -eq "1" ]; then
        echo "error in file_$COUNTER"
        ((ERROR_COUNTER+=1))
    fi
    ((COUNTER+=1))
done
echo "$COUNTER duckdb files have been read, nr of (graceful) errors: '$ERROR_COUNTER'"
rm -rf ./tmp/
