#!/bin/bash

# this script tests if the csv files in a directory can be read

# NOTE: set path to duckdb executable, compiled with: BUILD_JSON=1 CRASH_ON_ASSERT=1
DUCKDB_EXECUTABLE_FULLPATH="/path-to-duckdb/duckdb"

# NOTE: set the correct CSV_INPUT_FILE_DIR and ARGUMENT_STRING per error case
CSV_INPUT_FILE_DIR="/my-path/csv_issues/scenario_15_ignore_errors"
ARGUMENT_STRING=", ignore_errors=true"

# CSV_INPUT_FILE_DIR="/my-path/csv_issues/scenario_20_null_padding"
# ARGUMENT_STRING=", null_padding=true"

# CSV_INPUT_FILE_DIR="/my-path/csv_issues/scenario_26_skip"
# ARGUMENT_STRING=", skip=1"

# CSV_INPUT_FILE_DIR="/my-path/csv_issues/scenario_without_params"
# ARGUMENT_STRING=""

CRASH_LOG=crash.log
CHECK_ERRORS=false

ANSI_RED="\x1b[31m"
ANSI_GREEN="\x1b[32m"
ANSI_CYAN="\x1b[36m"
ANSI_RESET="\x1b[0m"

COUNTER=0
ERROR_COUNTER=0
CRASH_COUNTER=0

> $CRASH_LOG
for file_path in $CSV_INPUT_FILE_DIR/*;
do
    if [ -f $file_path ]; then
        { $DUCKDB_EXECUTABLE_FULLPATH -c "SELECT * FROM read_csv('$file_path' $ARGUMENT_STRING);" 1> /dev/null; } 2> tmpfile
        exit_status=$?
        if [ "$exit_status" -ne "0" ]; then
            # echo "NOK"
            file_name=$(basename ${file_path})
            # echo $file_name
            if [ "$exit_status" -eq "1" ]; then
                if $CHECK_ERRORS ; then
                    echo "error when reading $file_name, exit status: $exit_status"
                    echo "error when reading $file_name, exit status: $exit_status" >> $CRASH_LOG
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
        else
            echo "OK"
        fi
        ((COUNTER+=1))
    fi
done
echo -e "${ANSI_GREEN}$COUNTER csv files have been read; ${ANSI_RED}nr of crashes: $CRASH_COUNTER; ${ANSI_CYAN}nr of errors: '$ERROR_COUNTER'${ANSI_RESET}"
echo "see \"$CRASH_LOG\" for more details"
rm -f tmpfile
