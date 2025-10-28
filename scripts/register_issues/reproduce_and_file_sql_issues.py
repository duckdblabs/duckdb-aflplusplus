#!/usr/bin/env python3

import os
from pathlib import Path
import sys

import fuzzer_helper
import github_helper


def main(argv: list[str]):
    # default inputs (for local reproduction)
    fuzz_results_dir = Path("~/Desktop/fuzz_results/sql_fuzzer/default").expanduser()
    duckdb_cli = Path("~/git/duckdb/build/debug/duckdb").expanduser()

    if len(argv) > 1:
        fuzz_results_dir = Path(argv[1]).expanduser()
    if len(argv) > 2:
        duckdb_cli = Path(argv[2]).expanduser()

    # verify duckdb_cli can be found
    if not duckdb_cli.is_file():
        raise ValueError(f"expected file not found: {duckdb_cli}")

    # reproduce crashes and hangs
    unique_issues = fuzzer_helper.reproduce_crashes_from_sql_dir(fuzz_results_dir / "crashes", duckdb_cli)
    unique_hangs = fuzzer_helper.reproduce_crashes_from_sql_dir(fuzz_results_dir / "hangs", duckdb_cli, max_one=True)
    unique_issues.update(unique_hangs)
    print(f"{len(unique_issues)} total unique and reproducible errors found by fuzzer")

    # only keep new issues
    new_issues = {}
    for issue in unique_issues.values():
        sql_statement, exception_msg, stacktrace = issue
        title = exception_msg[:200]
        if not github_helper.is_known_github_issue(title):
            new_issues[exception_msg] = (title, sql_statement, exception_msg, stacktrace)
    print(f"{len(new_issues)} new issues found by fuzzer")

    # create github issues
    for issue in new_issues.values():
        title, sql_statement, exception_msg, stacktrace = issue
        fuzzer_helper.file_issue(
            title, sql_statement, exception_msg, stacktrace, "sql_fuzzer", 0, os.environ['DUCKDB_SHA']
        )


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
