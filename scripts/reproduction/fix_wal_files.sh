#!/bin/bash

# NOTE: run this script before running 'wal_replay.sh' !!
# running this script is needed to reproduce wal file crash cases found by the afl++ fuzzer

# This script transforms the crude .wal files to 'passable' .wal files by fixing the checksums and file sizes.
# This fixup step also takes place in the fuzzing process, and is therefore also needed to reproduce the error.

# outputs:
# - numbered wal files: 'db_0.wal', 'db_1.wal', etc

# NOTE: all these wal files contain mutations with respect to the same 'base_db'.
# To recreate the errors, use script: 'test_wal_output.sh'

WAL_FILES_IN_DIR="../fuzz_results/wal_fuzzer/default/crashes"
WAL_FILES_OUT_DIR="./tmp"
mkdir -p $WAL_FILES_OUT_DIR

COUNTER=0
for wal_file_src in $WAL_FILES_IN_DIR/*;
do
    wal_file_dst="${WAL_FILES_OUT_DIR}/db_${COUNTER}.wal"
    cp $wal_file_src $wal_file_dst
    python3 ../fuzz_utils/fix_wal_file.py $wal_file_dst
    ((COUNTER+=1))
done
echo "$COUNTER wal files have fixed and stored in directory: $WAL_FILES_OUT_DIR"
