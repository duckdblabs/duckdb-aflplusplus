#!/bin/bash

# this script tests if the parquet files in the directory can be read

# -------- START user settings:
PARQUET_INPUT_FILE_DIR="$HOME/Desktop/crashes"

# NOTE: compile duckdb with CRASH_ON_ASSERT=1 to also check for internal exceptions!
DUCKDB_EXECUTABLE_FULLPATH="$HOME/git/duckdb/build/release/duckdb"
# -------- END user settings


CRASH_LOG=crash.log

ANSI_RED="\x1b[31m"
ANSI_GREEN="\x1b[32m"
ANSI_RESET="\x1b[0m"

COUNTER=0
CRASH_COUNTER=0

> $CRASH_LOG
for file_path in $PARQUET_INPUT_FILE_DIR/*;
do
    if [ -f $file_path ]; then
        { $DUCKDB_EXECUTABLE_FULLPATH -c "SELECT * FROM read_parquet('$file_path');" 1> /dev/null; } 2> tmpfile
        exit_status=$?
        if ([ $exit_status -ne 0 ] && [ $exit_status -ne 1 ]); then
            file_name=$(basename ${file_path})
            echo "CRASH when reading $file_name, exit status: $exit_status"
            echo "CRASH when reading $file_name, exit status: $exit_status" >> $CRASH_LOG
            cat tmpfile >> $CRASH_LOG
            echo "" >> $CRASH_LOG
            ((CRASH_COUNTER+=1))
        fi
        ((COUNTER+=1))
    fi
done

echo -e "${ANSI_GREEN}$COUNTER parquet files have been read; ${ANSI_RED}nr of crashes: $CRASH_COUNTER${ANSI_RESET}"
echo "see \"$CRASH_LOG\" for more details"
rm -f tmpfile
