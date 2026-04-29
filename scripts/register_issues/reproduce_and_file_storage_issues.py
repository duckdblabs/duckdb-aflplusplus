#!/usr/bin/env python3

'''
This script reproduces crash cases reads duckdb storage that were found by the fuzzer to be
'''

from pathlib import Path
import sys

from fuzzer_helper import run_sql
import github_helper
import re


def reproduce_storage_crashes(storage_file_dir: Path, duckdb_cli: Path, max_one=False):
    unique_crashes = {}
    all_storage_files = sorted(storage_file_dir.iterdir())

    print(f"reproducing errors in {len(all_storage_files)} storage files in dir {storage_file_dir} ...")
    for storage_file in all_storage_files:
        sql_statement_bytes = f"ATTACH '{storage_file}' AS tmp_db (READ_ONLY); use tmp_db; show tables;".encode()
        exception_msg, stacktrace = run_sql(duckdb_cli, sql_statement_bytes, 'storage_fuzzer')
        if exception_msg:
            # ignore duplicates error messages that only have different numbers
            exception_msg_pruned = re.sub(r'\d+', '', exception_msg)
            unique_crashes[exception_msg_pruned] = (sql_statement_bytes, exception_msg, stacktrace)
            if max_one:
                break
    return unique_crashes


def main(argv: list[str]):
    # default inputs (for local reproduction)
    fuzz_results_dir = Path("~/Desktop/fuzz_results/storage_fuzzer/default").expanduser()
    duckdb_cli = Path("~/git/duckdb/build/debug/duckdb").expanduser()

    if len(argv) > 1:
        fuzz_results_dir = Path(argv[1]).expanduser()
    if len(argv) > 2:
        duckdb_cli = Path(argv[2]).expanduser()

    # verify duckdb_cli can be found
    if not duckdb_cli.is_file():
        raise ValueError(f"expected file not found: {duckdb_cli}")


    # TODO: add hangs
    crash_dir = fuzz_results_dir / 'crashes'
    unique_issues = reproduce_storage_crashes(crash_dir, duckdb_cli)

    # only keep new issues
    new_issues = {}
    for issue in unique_issues.values():
        sql_statement_bytes, exception_msg, stacktrace = issue
        title = exception_msg[:200]
        if not github_helper.is_known_github_issue(title):
            new_issues[exception_msg] = (title, sql_statement_bytes, exception_msg, stacktrace)
    print(f"{len(new_issues)} new issues found by fuzzer")


if __name__ == "__main__":
    if len(sys.argv) not in range(1, 4):
        sys.exit(
            """
            ERROR; call this script with the following arguments:
              1 - (optional) path to fuzz_results directory
              2 - (optional) path to duckdb cli (executable)
            """
        )
    main(sys.argv)
