#!/usr/bin/env python3

'''
Script to create sqllogic tests in a duckdb repository, based on fuzz results
NOTE: first run script 'decode_multi_param_files.py' to create reproductions from raw fuzzer output!
compatible with fuzz scenarios:
  - fuzz_csv_multi_param
  - fuzz_json_multi_param
  - fuzz_parquet_multi_param
Input is equal to Output of 'decode_multi_param_files.py':
  - a directory of csv, json or parquet files
  - this directory should also contain file _REPRODUCTIONS.json that contains the argument string per data file
Output:
  - a directory with sqllogic tests is created in the duckdb repo (or an other location)
  - the csv/json/parquet data files used by these tests are copied to the the duckdb repo
'''

import json
from io import TextIOWrapper
from pathlib import Path
import shutil
import sys
import time


def main(argv: list[str]):
    file_reader_function = argv[1]  # read_csv / read_json / read_parquet
    file_type = file_reader_function.rpartition('_')[2]  # csv / json / parquet

    # default paths
    REPRODUCTION_DIR = Path("~/Desktop/reproductions").expanduser()
    DUCKDB_REPO = Path("~/git/duckdb").expanduser()
    SQLLOGIC_DIR = DUCKDB_REPO / f'test/fuzzer/afl/{file_type}'
    if len(argv) > 2:
        REPRODUCTION_DIR = Path(argv[2]).expanduser()
    if len(argv) > 3:
        SQLLOGIC_DIR = Path(argv[3]).expanduser()
    if len(argv) > 4:
        DUCKDB_REPO = Path(argv[4]).expanduser()

    date_str = time.strftime(r"%Y%m%d")
    match file_reader_function:
        case 'read_csv':
            duckdb_data_dir = f'data/csv/afl/{date_str}_csv_fuzz_error'
            required_duckdb_extension = ''
            enable_verification = True
        case 'read_json':
            duckdb_data_dir = f'data/json/afl/{date_str}_json_fuzz_error'
            required_duckdb_extension = 'json'
            enable_verification = True
        case 'read_parquet':
            duckdb_data_dir = f'data/parquet-testing/afl/{date_str}_parquet_fuzz_error'
            required_duckdb_extension = 'parquet'
            enable_verification = False
        case _:
            raise ValueError(f"invalid input: {file_reader_function}")

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
    SQLLOGIC_DIR.mkdir(parents=True, exist_ok=True)
    sqllogic_test_file = SQLLOGIC_DIR / f"fuzz_{date_str}.test"
    sqllogic_test_name = f'test/fuzzer/afl/{file_type}/fuzz_{date_str}.test'
    with sqllogic_test_file.open('w') as test_file:
        add_test_header(test_file, sqllogic_test_name, file_type, required_duckdb_extension, enable_verification)
        add_count_test(test_file, duckdb_data_dir, len(reproduction_data))
        for repro_item in reproduction_data:
            add_test(
                test_file,
                file_reader_function,
                duckdb_data_dir + '/' + repro_item['file_name'],
                ", " + repro_item['arguments'],
            )
    print(f"created '{sqllogic_test_file}'")

    # if the sqllogic test file is created in the duckdb repo, also copy the data files to this repo
    # so the test can be run afterwards
    if sqllogic_test_file == (DUCKDB_REPO / sqllogic_test_name):
        (DUCKDB_REPO / duckdb_data_dir).mkdir(parents=True, exist_ok=True)
        for repro_item in reproduction_data:
            file_name = repro_item['file_name']
            src_file = REPRODUCTION_DIR / file_name
            dst_file = DUCKDB_REPO / duckdb_data_dir / file_name
            shutil.copy(src_file, dst_file)
        print(f"copied {len(reproduction_data)} test data files to {DUCKDB_REPO / duckdb_data_dir}")
        print(f"run test with:")
        print(f"{DUCKDB_REPO}/build/release/test/unittest {sqllogic_test_name}")


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
    if len(sys.argv) not in [2, 3, 4, 5]:
        sys.exit(
            """
            ERROR; call this script with the following arguments:
              1 - target function ('read_csv', 'read_json' or 'read_parquet')
              2 - (optional) input path to reproductions directory (created by decode_multi_param_files.py)
              3 - (optional) output dir to create sqllogic tests (default = create in duckdb repo)
              4 - (optional) input path to duckdb directory (root)
            """
        )
    main(sys.argv)
