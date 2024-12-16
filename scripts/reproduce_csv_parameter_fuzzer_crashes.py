#!/usr/bin/env python3

'''
Script to reproduce the crash-cases created by the csv_parameter_fuzzer
Note that the content of 'SCENARIOS' should be equal to the scenarios used in csv_parameter_fuzzer.cpp
to correctly reproduce the error case
'''

from pathlib import Path
import subprocess
import shutil

# duckdb should be compiled with: BUILD_JSON=1 CRASH_ON_ASSERT=1
DUCKDB_PATH = Path("~/git/duckdb/build/release/duckdb").expanduser()
FUZZ_RESULT_PATH = Path("~/Desktop/crashes").expanduser()
REPRODUCTION_PATH = Path("~/Desktop/csv_issues").expanduser()

# scenarios copied from csv_parameter_fuzzer.cpp
SCENARIOS = [
    "all_varchar=true",
    "allow_quoted_nulls=false",
    "auto_detect=false",
    "auto_type_candidates = ['BIGINT', 'DATE']",
    "columns = {'col1': 'INTEGER', 'col2': 'VARCHAR'}",
    "auto_detect=false, columns = {'col1': 'INTEGER', 'col2': 'VARCHAR'}",
    "compression=gzip",
    "dateformat='%d/%m/%Y'",
    "decimal_separator=','",
    "delim='@'",
    "escape='@'",
    "filename=true",
    "force_not_null=[a]",
    "header=false",
    "hive_partitioning=true",
    "ignore_errors=true",
    "max_line_size=10",
    "names=['apple','pear','banana']",
    "new_line='\\r\\n'",
    "normalize_names=true",
    "null_padding=true",
    "nullstr=['a', 'b']",
    "parallel=false",
    "quote=@",
    "sample_size=1",
    "sep='('",
    "skip=1",
    "timestampformat='%A, %-d %B %Y - %I:%M:%S %p'",
    "types=['INTEGER','INTEGER']",
    "dtypes={'a': 'DATE'}",
    "union_by_name=true",
]


def main():
    REPRODUCTION_PATH.mkdir(parents=True, exist_ok=True)

    count = 0
    for fuzz_file in sorted(FUZZ_RESULT_PATH.iterdir()):
        content = bytearray(fuzz_file.read_bytes())

        # determine scenario based on first byte
        scenario_idx = content.pop(0) % len(SCENARIOS)
        arguments = SCENARIOS[scenario_idx]

        # create input file for reproduction: NOTE: first byte has been popped!
        newfile = REPRODUCTION_PATH / f"case_{count}"
        newfile.write_bytes(content)

        # try to reproduce without extra arguments
        res = subprocess.run(f"{DUCKDB_PATH} -c \"select * from read_csv('{newfile}');\"", shell=True, capture_output=True)
        if res.returncode < 0 or res.returncode > 1:
            scenariodir = REPRODUCTION_PATH / f"scenario_without_params"
            scenariodir.mkdir(parents=True, exist_ok=True)
            shutil.move(newfile, scenariodir)
            print(f"{newfile.name} - NO ARG - {res.stderr}")
        else:
            # try to reproduce with extra arguments
            res = subprocess.run(f"{DUCKDB_PATH} -c \"select * from read_csv('{newfile}', {arguments});\"", shell=True, capture_output=True)
            if res.returncode < 0 or res.returncode > 1:
                scenariodir = REPRODUCTION_PATH / f"scenario_{scenario_idx}_{arguments.split('=')[0].strip()}"
                scenariodir.mkdir(parents=True, exist_ok=True)
                shutil.move(newfile, scenariodir)
                print(f"{newfile.name} - {arguments} - {res.stderr}")
            else:
                newfile.unlink()  # delete the file, only keep reproducible cases
                print(f"{newfile.name}: non-rep; return code: {res.returncode}")

        count += 1


if __name__ == "__main__":
    main()
