#!/usr/bin/env python3

import json
import os
from pathlib import Path
import sys

import fuzzer_helper
import github_helper


def reproduce_crashes(reproduction_dir: Path, duckdb_cli, file_reader_function):
    unique_crashes = {}
    # verify file _REPRODUCTIONS.json exists
    crashes_json_file = reproduction_dir / 'crashes/_REPRODUCTIONS.json'
    if not crashes_json_file.is_file():
        print(f"no crashes found; file not present: {crashes_json_file}")
        return unique_crashes
    with open(crashes_json_file, 'r') as repr_file_fd:
        reproduction_data: list = json.load(repr_file_fd)
    # verify REPRODUCTION_DIR contains the expected data files
    for repro_item in reproduction_data:
        repro_file_path = reproduction_dir / 'crashes' / repro_item['file_name']
        if not repro_file_path.is_file():
            raise ValueError(f"file not found: {repro_file_path}")
    # reproduce crashes
    count_reproducible = 0
    for repro_item in reproduction_data:
        repro_file_path = reproduction_dir / 'crashes' / repro_item['file_name']
        arguments = ", " + repro_item['arguments'] if repro_item['arguments'] else ""
        exception_msg, stacktrace = fuzzer_helper.reproduce_filereader_issue(
            duckdb_cli, repro_file_path, file_reader_function, arguments
        )
        if exception_msg:
            count_reproducible += 1
        if exception_msg and exception_msg not in unique_crashes:
            unique_crashes[exception_msg] = (repro_file_path, arguments, exception_msg, stacktrace)
        print(f"{len(reproduction_data)} crashes found by fuzzer")
        print(f"{count_reproducible} crashes could be reproduced")
        print(f"{len(unique_crashes)} crashes are unique")
    return unique_crashes


def reproduce_hangs(reproduction_dir, duckdb_cli, file_reader_function):
    unique_hangs = {}
    # verify file _REPRODUCTIONS.json exists
    hangs_json_file = reproduction_dir / 'hangs/_REPRODUCTIONS.json'
    if not hangs_json_file.is_file():
        print(f"no hangs found; (file not present: {hangs_json_file})")
        return unique_hangs
    with open(hangs_json_file, 'r') as repr_file_fd:
        reproduction_data: list = json.load(repr_file_fd)
    # verify REPRODUCTION_DIR contains the expected data files
    for repro_item in reproduction_data:
        repro_file_path = reproduction_dir / 'hangs' / repro_item['file_name']
        if not repro_file_path.is_file():
            raise ValueError(f"file not found: {repro_file_path}")
    # reproduce hangs (return as soon as 1 has been found)
    print(f"{len(reproduction_data)} hangs found by fuzzer")
    for repro_item in reproduction_data:
        repro_file_path = reproduction_dir / 'hangs' / repro_item['file_name']
        arguments = ", " + repro_item['arguments'] if repro_item['arguments'] else ""
        exception_msg, stacktrace = fuzzer_helper.reproduce_filereader_issue(
            duckdb_cli, repro_file_path, file_reader_function, arguments
        )
        if exception_msg:
            unique_hangs[exception_msg] = (repro_file_path, arguments, exception_msg, stacktrace)
            print(f"hang could be reproduced (adding one unique case)")
            return unique_hangs
    print("hang could not be reproduced")
    return unique_hangs


def main(argv: list[str]):
    fuzz_scenario = argv[1]
    match fuzz_scenario:
        case 'csv_multi_param_fuzzer':
            file_reader_function = 'read_csv'
            file_type = 'csv'
        case 'json_multi_param_fuzzer':
            file_reader_function = 'read_json'
            file_type = 'json'
        case 'parquet_multi_param_fuzzer':
            file_reader_function = 'read_parquet'
            file_type = 'parquet'
        case _:
            raise ValueError(f"invalid input: {file_reader_function}")

    # default inputs (for local reproduction)
    REPRODUCTION_DIR = Path("~/Desktop/reproductions").expanduser()
    DUCKDB_DIR = Path("~/git/duckdb").expanduser()
    DUCKDB_FUZZER_DIR = Path("~/git/duckdb-fuzzer").expanduser()

    if len(argv) > 2:
        REPRODUCTION_DIR = Path(argv[2]).expanduser()
    if len(argv) > 3:
        DUCKDB_DIR = Path(argv[3]).expanduser()
    if len(argv) > 4:
        DUCKDB_FUZZER_DIR = Path(argv[4]).expanduser()

    # verify duckdb_cli can be found
    duckdb_cli = DUCKDB_DIR / "build/release/duckdb"
    if not duckdb_cli.is_file():
        raise ValueError(f"expected file not found: {duckdb_cli}")

    # reproduce crashes (keep unique crashes)
    unique_issues = reproduce_crashes(REPRODUCTION_DIR, duckdb_cli, file_reader_function)

    # reproduce hangs (keep max 1)
    unique_hangs = reproduce_hangs(REPRODUCTION_DIR, duckdb_cli, file_reader_function)
    unique_issues.update(unique_hangs)
    print(f"{len(unique_issues)} total unique and reproducible errors found by fuzzer")

    # only keep new issues
    rel_file_dir = f"reproduction_inputs/{file_type}"
    new_issues = {}
    for issue in unique_issues.values():
        repro_file_path, arguments, exception_msg, stacktrace = issue
        title = exception_msg[:200]
        if not github_helper.is_known_github_issue(title):
            repro_file_name = repro_file_path.name
            rel_file_path = f"{rel_file_dir}/{repro_file_name}"
            sql_statement_gh = f".sh wget {github_helper.file_url(rel_file_path)}\nfrom {file_reader_function}('{repro_file_name}'{arguments});"
            new_issues[exception_msg] = (title, rel_file_path, repro_file_path, sql_statement_gh, exception_msg, stacktrace)
    print(f"{len(new_issues)} new issues found by fuzzer")

    # commit reproduction files
    if new_issues:
        fuzzer_helper.run_command(f"mkdir -p {DUCKDB_FUZZER_DIR / rel_file_dir}")
        for issue in new_issues.values():
            title, rel_file_path, repro_file_path, sql_statement_gh, exception_msg, stacktrace = issue
            fuzzer_helper.run_command(f"cp {repro_file_path} {DUCKDB_FUZZER_DIR / rel_file_path}")
        fuzzer_helper.run_command(f"git -C {DUCKDB_FUZZER_DIR} add .")
        fuzzer_helper.run_command(
            f"git -C {DUCKDB_FUZZER_DIR} commit -m 'add reproduction file for afl++ fuzz run {os.environ.get('FUZZ_RUN_ID')}'"
        )
        fuzzer_helper.run_command(
            f"git -C {DUCKDB_FUZZER_DIR} push || (git -C {DUCKDB_FUZZER_DIR} config pull.rebase true && git -C {DUCKDB_FUZZER_DIR} pull && git -C {DUCKDB_FUZZER_DIR} push)"
        )

    # create github issues
    for issue in new_issues.values():
        title, rel_file_path, repro_file_path, sql_statement_gh, exception_msg, stacktrace = issue
        fuzzer_helper.file_issue(
            title, sql_statement_gh, exception_msg, stacktrace, os.environ['FUZZ_SCENARIO'], 0, os.environ['DUCKDB_SHA']
        )


if __name__ == "__main__":
    if len(sys.argv) not in range(2, 6):
        sys.exit(
            """
            ERROR; call this script with the following arguments:
              1 - fuzz scenario ('csv_multi_param_fuzzer', 'json_multi_param_fuzzer' or 'parquet_multi_param_fuzzer')
              2 - (optional) path to reproductions directory (created by decode_multi_param_files.py)
              3 - (optional) path to duckdb directory
              4 - (optional) path to /duckdb/duckdb-fuzzer directory
            """
        )
    main(sys.argv)
