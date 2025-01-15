#!/usr/bin/env python3

'''
Script to create sqllogic tests based on fuzz results (fuzz-csv-multi-param, fuzz-json-multi-param).
NOTE: first run script 'decode_multi_param_files.py' to create reproductions from raw fuzzer output
'''

import json
from io import TextIOWrapper
from pathlib import Path
import shutil
import sys
import time

# input:
# set your local duckdb repo!
DUCKDB_REPO = Path("~/git/duckdb").expanduser()
# note: run script 'decode_multi_param_files.py' to create reproductions from raw fuzzer output
REPRODUCTIONS = Path("~/Desktop/reproductions").expanduser()

# output:
# sqllogic tests and data files are created in the duckdb repo


def main(argv: list):
    file_reader_function = argv[1]
    date_str = time.strftime(r"%Y%m%d")
    match file_reader_function:
        case 'read_csv':
            data_dir = DUCKDB_REPO / f'data/csv/afl/{date_str}_csv_fuzz_error'
            sqllogic_test_dir = DUCKDB_REPO / f'test/fuzzer/afl/csv'
            sqllogic_test_file = sqllogic_test_dir / f"fuzz_{date_str}.test"
            test_group = 'csv'
            required_extension = ''
            enable_verification = True
        case 'read_json':
            data_dir = DUCKDB_REPO / f'data/csv/afl/{date_str}_json_fuzz_error'
            sqllogic_test_dir = DUCKDB_REPO / f'test/fuzzer/afl/json'
            sqllogic_test_file = sqllogic_test_dir / f"fuzz_{date_str}.test"
            test_group = 'json'
            required_extension = 'json'
            enable_verification = True
        case _:
            raise ValueError(f"invalid input: {file_reader_function}")

    # verify reproductions exists
    reproductions_json_file = REPRODUCTIONS / '_REPRODUCTIONS.json'
    if not reproductions_json_file.is_file():
        raise ValueError(f"expected file not found: {reproductions_json_file}")
    with open(reproductions_json_file, 'r') as repr_file_fd:
        reproduction_data: list = json.load(repr_file_fd)

    # copy datafiles to duckdb repo
    data_dir.mkdir(parents=True, exist_ok=True)
    for repro_item in reproduction_data:
        file_name = repro_item['file_name']
        # copy file to duckdb data dir
        src_file = REPRODUCTIONS / file_name
        dst_file = data_dir / repro_item['file_name']
        if not src_file.is_file():
            raise ValueError(f"file not found: {src_file}")
        else:
            shutil.copy(src_file, dst_file)
    print(f"copied {len(reproduction_data)} test data files to {data_dir}")

    # create sqllogic tests
    sqllogic_test_dir.mkdir(parents=True, exist_ok=True)
    rel_test_file_path = sqllogic_test_file.relative_to(DUCKDB_REPO)
    with sqllogic_test_file.open('w') as test_file:
        add_test_header(test_file, rel_test_file_path, test_group, required_extension, enable_verification)
        add_count_test(test_file, data_dir.relative_to(DUCKDB_REPO), len(reproduction_data))
        for repro_item in reproduction_data:
            add_test(
                test_file,
                file_reader_function,
                data_dir.relative_to(DUCKDB_REPO) / repro_item['file_name'],
                ", " + repro_item['arguments'],
            )
    print(f"created '{sqllogic_test_file}'; run it with:")
    print(f"{DUCKDB_REPO}/build/release/test/unittest {sqllogic_test_file.relative_to(DUCKDB_REPO)}")


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
    if len(sys.argv) < 2:
        sys.exit("ERROR. provide the target function to scrape ('read_csv' or 'read_json') as first argument")
    main(sys.argv)
