#!/bin/bash

# this script tests if the parquet files in the directory can be read
PARQUET_INPUT_FILE_DIR="/path-to-parquet-files/"
DUCKDB_EXECUTABLE_FULLPATH="/path-to-duckdb/duckdb"
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
for file_path in $PARQUET_INPUT_FILE_DIR/*;
do
    if [ -f $file_path ]; then
        { $DUCKDB_EXECUTABLE_FULLPATH -c "SELECT * FROM read_parquet('$file_path');" 1> /dev/null; } 2> tmpfile
        exit_status=$?
        if [ "$exit_status" -ne "0" ]; then
            file_name=$(basename ${file_path})
            if [ "$exit_status" -eq "1" ]; then
                if $CHECK_INTERNAL_ERRORS ; then
                    echo "INTERNAL error when reading $file_name, exit status: $exit_status"
                    echo "INTERNAL error when reading $file_name, exit status: $exit_status" >> $CRASH_LOG
                    cat tmpfile >> $CRASH_LOG
                    echo "" >> $CRASH_LOG
                fi
                ((ERROR_COUNTER+=1))
            else
                echo "CRASH when reading $file_name, exit status: $exit_status"
                echo "CRASH when reading $file_name, exit status: $exit_status" >> $CRASH_LOG
                cat tmpfile >> $CRASH_LOG
                echo "" >> $CRASH_LOG
                ((CRASH_COUNTER+=1))
            fi
        fi
        ((COUNTER+=1))
    fi
done
echo -e "${ANSI_GREEN}$COUNTER parquet files have been read; ${ANSI_RED}nr of crashes: $CRASH_COUNTER; ${ANSI_CYAN}nr of internal errors: '$ERROR_COUNTER'${ANSI_RESET}"
echo "see \"$CRASH_LOG\" for more details"
rm -f tmpfile
