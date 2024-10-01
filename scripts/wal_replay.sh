#!/bin/bash

# this script reproduces the errors found by: wal_fuzzer

# !! NOTE:
#  - all wal files in WAL_FILES_DIR need to contain mutations with respect to the same 'base_db'.
#  - before running the script, be sure the checksums are fixed (use 'fix_wal_files.sh' if needed)
WAL_FILES_DIR="./tmp"
BASE_DB_PATH="../build/base_db"

DUCKDB_EXECUTABLE_FULLPATH="/opt/homebrew/bin/duckdb"
TEMP_DB='./tmpdb'
TEMP_ERROR='./tmperror'
CRASH_LOG=crash.log
CHECK_INTERNAL_ERRORS=false

ANSI_RED="\x1b[31m"
ANSI_GREEN="\x1b[32m"
ANSI_CYAN="\x1b[36m"
ANSI_RESET="\x1b[0m"

COUNTER=0
ERROR_COUNTER=0
CRASH_COUNTER=0

> $CRASH_LOG
for wal_file in $WAL_FILES_DIR/*;
do
    # make sure the db-storage file and the wal have corresponding names
    cp $BASE_DB_PATH $TEMP_DB  # 'base_db' needs to be refreshed every loop!
    cp $wal_file "${TEMP_DB}.wal"

    { $DUCKDB_EXECUTABLE_FULLPATH -c "ATTACH '$TEMP_DB' AS tmp_db (READ_ONLY); use tmp_db; show tables;" 1> /dev/null; } 2> $TEMP_ERROR
    exit_status=$?
    if [ "$exit_status" -ne "0" ]; then
        wal_name=$(basename ${wal_file})
        if [ "$exit_status" -eq "1" ]; then
            if $CHECK_INTERNAL_ERRORS ; then
                echo "error when reading $wal_name, exit status: $exit_status"
                echo "error when reading $wal_name, exit status: $exit_status" >> $CRASH_LOG
                cat $TEMP_ERROR >> $CRASH_LOG
                echo "" >> $CRASH_LOG
            fi
            ((ERROR_COUNTER+=1))
        else
            echo -e "${ANSI_RED}CRASH when reading $wal_name, exit status: $exit_status${ANSI_RESET}"
            echo "CRASH when reading $wal_name, exit status: $exit_status" >> $CRASH_LOG
            cat $TEMP_ERROR >> $CRASH_LOG
            echo "" >> $CRASH_LOG
            ((CRASH_COUNTER+=1))
        fi
    fi
    ((COUNTER+=1))
done

echo -e "${ANSI_GREEN}$COUNTER wal files have been processed; ${ANSI_RED}nr of crashes: $CRASH_COUNTER; ${ANSI_CYAN}nr of (internal) errors: '$ERROR_COUNTER'${ANSI_RESET}"
echo "see \"$CRASH_LOG\" for more details"
rm -f $TEMP_ERROR
rm -f $TEMP_DB
rm -f "${TEMP_DB}.wal"
