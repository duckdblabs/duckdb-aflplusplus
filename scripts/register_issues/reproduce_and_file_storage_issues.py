#!/usr/bin/env python3

'''
This script reproduces crash cases that were found by the duckdb storage file fuzzer.
Before running this script, the 'raw' crash cases should be pre-processed with script: scripts/fuzz_utils/fix_duckdb_file.py
'''

import os
from pathlib import Path
import re
import sys
import time
import uuid

import fuzzer_helper
import github_helper


def reproduce_storage_errors(storage_file_dir: Path, duckdb_cli: Path, max_one=False):
    unique_errors = {}
    all_storage_files = sorted(storage_file_dir.iterdir())

    print(f"reproducing errors in {len(all_storage_files)} storage files in dir {storage_file_dir} ...")
    for repro_file_path in all_storage_files:
        sql_statement = f"ATTACH '{repro_file_path}' AS tmp_db (READ_ONLY); use tmp_db; show tables;"
        exception_msg, stacktrace = fuzzer_helper.run_sql(duckdb_cli, sql_statement.encode(), 'storage_fuzzer')
        if exception_msg:
            # ignore duplicates error messages that only have different numbers (only keep different line numbers from assertion errors)
            exception_msg_pruned = re.sub(r'(?<!line )\b\d+\b', '', exception_msg)

            unique_errors[exception_msg_pruned] = (repro_file_path, exception_msg, stacktrace)

            if max_one:
                break
    return unique_errors


def main(argv: list[str]):
    # default inputs (for local reproduction)
    fuzz_results_dir = Path("~/Desktop/fuzz_results/storage_fuzzer/default").expanduser()
    duckdb_cli = Path("~/git/duckdb/build/relassert/duckdb").expanduser()
    duckdb_fuzzer_dir = Path("~/git/duckdb-fuzzer").expanduser()

    if len(argv) > 1:
        fuzz_results_dir = Path(argv[1]).expanduser()
    if len(argv) > 2:
        duckdb_cli = Path(argv[2]).expanduser()
    if len(argv) > 3:
        duckdb_fuzzer_dir = Path(argv[3]).expanduser()

    # if 'FUZZEROFDUCKSKEY' is missing we assume it is a dry run
    dry_run = False if ('FUZZEROFDUCKSKEY' in os.environ and len(os.environ['FUZZEROFDUCKSKEY']) > 0) else True

    # verify duckdb_cli can be found
    if not duckdb_cli.is_file():
        raise ValueError(f"expected file not found: {duckdb_cli}")

    # only keep unique reproducible issues
    unique_issues = reproduce_storage_errors(fuzz_results_dir / 'crashes', duckdb_cli)
    unique_hangs = reproduce_storage_errors(fuzz_results_dir / 'hangs', duckdb_cli, max_one=True)
    unique_issues.update(unique_hangs)
    print(f"{len(unique_issues)} total unique and reproducible errors found by fuzzer")

    # only keep new issues
    rel_file_dir = f"reproduction_inputs/duckdb_storage"
    new_issues = {}
    for issue in unique_issues.values():
        repro_file_path, exception_msg, stacktrace = issue
        title = exception_msg[:200]
        if not github_helper.is_known_github_issue(title):
            repro_file_name = f"{time.strftime(r"%Y%m%d")}_{uuid.uuid4().hex[:6]}.duckdb"
            rel_file_path = f"{rel_file_dir}/{repro_file_name}"
            sql_statement_gh = f".sh wget {github_helper.file_url(rel_file_path)}\nATTACH '{repro_file_name}' AS tmp_db (READ_ONLY); use tmp_db; show tables;"
            new_issues[exception_msg] = (title, rel_file_path, repro_file_path, sql_statement_gh, exception_msg, stacktrace)
    print(f"{len(new_issues)} new issues found by fuzzer")

    # dry run mode: early out
    if dry_run:
        print("running in dry run mode; no issues are created !")
        return

    # commit reproduction files
    if new_issues:
        fuzzer_helper.run_command(f"mkdir -p {duckdb_fuzzer_dir / rel_file_dir}")
        for issue in new_issues.values():
            title, rel_file_path, repro_file_path, sql_statement_gh, exception_msg, stacktrace = issue
            fuzzer_helper.run_command(f"cp {repro_file_path} {duckdb_fuzzer_dir / rel_file_path}")
        fuzzer_helper.run_command(f"git -C {duckdb_fuzzer_dir} add .")
        fuzzer_helper.run_command(
            f"git -C {duckdb_fuzzer_dir} commit -m 'add reproduction duckdb storage file for afl++ fuzz run {os.environ.get('FUZZ_RUN_ID')}'"
        )
        fuzzer_helper.run_command(
            f"git -C {duckdb_fuzzer_dir} push || (git -C {duckdb_fuzzer_dir} config pull.rebase true && git -C {duckdb_fuzzer_dir} pull && git -C {duckdb_fuzzer_dir} push)"
        )

    # create github issues
    for issue in new_issues.values():
        title, rel_file_path, repro_file_path, sql_statement_gh, exception_msg, stacktrace = issue
        fuzzer_helper.file_issue(
            title, sql_statement_gh, exception_msg, stacktrace, os.environ['FUZZ_SCENARIO'], 0, os.environ['DUCKDB_SHA']
        )


if __name__ == "__main__":
    if len(sys.argv) not in range(1, 5):
        sys.exit(
            """
            ERROR; call this script with the following arguments:
              1 - (optional) path to fuzz_results directory
              2 - (optional) path to duckdb cli (executable)
              3 - (optional) path to duckdb-fuzzer directory
            """
        )
    main(sys.argv)
