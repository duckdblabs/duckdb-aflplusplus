#!/usr/bin/env python3

'''
Script to create sqllogic tests in a duckdb repository, based on fuzz results
NOTE: first run script 'decode_multi_param_files.py' to create reproductions from raw fuzzer output!
compatible with fuzz scenarios:
  - fuzz_csv_multi_param
  - fuzz_json_multi_param
  - fuzz_parquet_multi_param
Input is equal to Output of 'decode_multi_param_files.py':
  - a directory of csv, json or parquet files (REPRODUCTION_DIR)
  - this directory should also contain file _REPRODUCTIONS.json that contains the argument string per data file
  - see code for other optional inputs
Output:
  - an sqllogic test file is created with a test per problematic input file
  - optional: if the the sqllogic test file is created in the duckdb repository, the csv/json/parquet data files
    used by these tests are also copied to the the duckdb repo
'''

import json
from io import TextIOWrapper
from pathlib import Path
import shutil
import sys
import time


def main(argv: list[str]):
    file_reader_function = argv[1]  # read_csv / read_json / read_parquet
    match file_reader_function:
        case 'read_csv':
            file_type = 'csv'
            required_duckdb_extension = 'json'
            enable_verification = True
        case 'read_json':
            file_type = 'json'
            required_duckdb_extension = 'json'
            enable_verification = True
        case 'read_parquet':
            file_type = 'parquet'
            required_duckdb_extension = 'parquet'
            enable_verification = False
        case _:
            raise ValueError(f"invalid input: {file_reader_function}")

    # default inputs (for local reproduction)
    date_str = time.strftime(r"%Y%m%d")
    duckdb_data_dirs = {
        "csv": f"data/csv/afl/{date_str}_csv_fuzz_error",
        "json": f"data/json/afl/{date_str}_json_fuzz_error",
        "parquet": f"data/parquet-testing/afl/{date_str}_parquet_fuzz_error",
    }
    REPRODUCTION_DIR = Path("~/Desktop/reproductions/crashes").expanduser()
    DUCKDB_DIR = Path("~/git/duckdb").expanduser()
    SQLLOGIC_TEST_NAME = f"test/fuzzer/afl/{file_type}/fuzz_{date_str}.test"
    SQLLOGIC_FILE_PATH = DUCKDB_DIR / SQLLOGIC_TEST_NAME
    SQLLOGIC_DATA_DIR = duckdb_data_dirs[file_type]

    # custom inputs
    if len(argv) > 2:
        REPRODUCTION_DIR = Path(argv[2]).expanduser()
    if len(argv) > 3:
        SQLLOGIC_TEST_NAME = argv[3]
    if len(argv) > 4:
        SQLLOGIC_FILE_PATH = Path(argv[4]).expanduser()
    if len(argv) > 5:
        SQLLOGIC_DATA_DIR = argv[5]
    if len(argv) > 6:
        DUCKDB_DIR = Path(argv[6]).expanduser()

    # verify file _REPRODUCTIONS.json exists
    reproductions_json_file = REPRODUCTION_DIR / '_REPRODUCTIONS.json'
    if not reproductions_json_file.is_file():
        raise ValueError(f"expected file not found: {reproductions_json_file}")
    with open(reproductions_json_file, 'r') as repr_file_fd:
        reproduction_data: list = json.load(repr_file_fd)

    # verify REPRODUCTION_DIR contains the expected data files
    for repro_item in reproduction_data:
        if not (REPRODUCTION_DIR / repro_item['file_name']).is_file():
            raise ValueError(f"file not found: {REPRODUCTION_DIR / file_name}")

    # create sqllogic tests
    SQLLOGIC_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SQLLOGIC_FILE_PATH.open('w') as test_file:
        add_test_header(test_file, SQLLOGIC_TEST_NAME, file_type, required_duckdb_extension, enable_verification)
        add_count_test(test_file, SQLLOGIC_DATA_DIR, len(reproduction_data))
        for repro_item in reproduction_data:
            add_test(
                test_file,
                file_reader_function,
                SQLLOGIC_DATA_DIR + '/' + repro_item['file_name'],
                ", " + repro_item['arguments'],
            )
    print(f"created '{SQLLOGIC_FILE_PATH}'")

    # if the sqllogic test file is created in the duckdb repo, also copy the data files to this repo
    # so the test can be run afterwards
    if SQLLOGIC_FILE_PATH == (DUCKDB_DIR / SQLLOGIC_TEST_NAME):
        (DUCKDB_DIR / SQLLOGIC_DATA_DIR).mkdir(parents=True, exist_ok=True)
        for repro_item in reproduction_data:
            file_name = repro_item['file_name']
            src_file = REPRODUCTION_DIR / file_name
            dst_file = DUCKDB_DIR / SQLLOGIC_DATA_DIR / file_name
            shutil.copy(src_file, dst_file)
        print(f"copied {len(reproduction_data)} test data files to {DUCKDB_DIR / SQLLOGIC_DATA_DIR}")
        print(f"run test with:")
        print(f"{DUCKDB_DIR}/build/release/test/unittest {SQLLOGIC_TEST_NAME}")


def add_test_header(test_file: TextIOWrapper, name: str, group: str, require: str, enable_verification: bool):
    header = f"""# name: {name}
# description: fuzzer generated {group} files - should not raise internal exception (by failed assertion).
# group: [{group}]

"""
    if require:
        header = header + f"require {require}\n\n"
    if enable_verification:
        header = header + "statement ok\nPRAGMA enable_verification\n\n"
    test_file.write(header)


def add_count_test(test_file: TextIOWrapper, data_dir: str, count: int):
    count_test = f"""query I
select count(file) from glob('./{data_dir}/*');
----
{count}

"""
    test_file.write(count_test)


def add_test(test_file: TextIOWrapper, file_reader_function: str, data_file: str, arguments: str):
    test = f"""statement maybe
FROM {file_reader_function}('{data_file}'{arguments});
----

"""
    test_file.write(test)


if __name__ == "__main__":
    if len(sys.argv) not in range(2, 8):
        sys.exit(
            """
            ERROR; call this script with the following arguments:
              1 - target function ('read_csv', 'read_json' or 'read_parquet')
              2 - (optional) path to reproductions directory (created by decode_multi_param_files.py)
              3 - (optional) sqllogic test name
              4 - (optional) full path to sqllogic test file to be created
              5 - (optional) sqllogic data dir
              6 - (optional) path to duckdb directory
            """
        )
    main(sys.argv)
