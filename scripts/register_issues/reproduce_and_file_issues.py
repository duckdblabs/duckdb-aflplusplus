#!/usr/bin/env python3

import json
from pathlib import Path
import sys
import subprocess
import time
import signal
import re
import fuzzer_helper
import github_helper
import uuid
import os


def is_internal_error(error):
    if 'differs from original result' in error:
        return True
    if 'INTERNAL' in error:
        return True
    if 'signed integer overflow' in error:
        return True
    if 'Sanitizer' in error or 'sanitizer' in error:
        return True
    if 'runtime error' in error:
        return True
    return False


def sanitize_stacktrace(err):
    err = re.sub(r'Stack Trace:\n', '', err)
    err = re.sub(r'../duckdb\((.*)\)', r'\1', err)
    err = re.sub(r'[\+\[]?0x[0-9a-fA-F]+\]?', '', err)
    err = re.sub(r'/lib/x86_64-linux-gnu/libc.so(.*)\n', '', err)
    return err.strip()


def split_exception_trace(exception_msg_full: str) -> tuple[str, str]:
    # exception message does not contain newline, so split after first newline
    exception_msg, _, stack_trace = sanitize_stacktrace(exception_msg_full).partition('\n')

    # cleaning:
    # if first line only contains =-symbols, skip it
    if re.fullmatch("=*", exception_msg):
        exception_msg, _, stack_trace = stack_trace.partition('\n')
    # if exception_msg is non-descritive AddressSanitizer issue, use first 2 lines of stack trace instead.
    if "AddressSanitizer: heap-buffer-overflow" in exception_msg and stack_trace:
        trace_lines = stack_trace.split('\n')
        # exception_msg = "AddressSanitizer: heap-buffer-overflow; " + stack_trace.partition('\n')[0]
        exception_msg = "AddressSanitizer: heap-buffer-overflow; " + '\n'.join(trace_lines[:2])

    return (exception_msg.strip(), stack_trace)


def run_command(command):
    res = os.system(command)
    if res != 0:
        print(f"command '{command}' failed with exit code: {res}")
        exit(res)


def reproduce_file_reader_issue(duckdb_cli, repro_file_path, file_reader_function, arguments):
    sql_statement = f"from {file_reader_function}('{repro_file_path}'{arguments})"
    (stdout, stderr, returncode, timed_out) = run_duckdb(duckdb_cli, sql_statement)
    match returncode:
        case 0:
            return ("", "")
        case 1 if not is_internal_error(stderr):  # regular error
            return ("", "")
        case 1:  # internal error
            exception_msg, stacktrace = split_exception_trace(stderr)
        case _ if returncode < 0:  # crash
            exception_msg, stacktrace = split_exception_trace(stderr)
            sig_name = signal.Signals(-returncode).name
            exception_msg = f"{sig_name}: {exception_msg}"
        case _ if timed_out: # hang
            exception_msg, stacktrace = (f"{file_reader_function} timed out after 300 s", "")
        case _:
            raise ValueError(f"undefined return code: {returncode} (expected 0, 1, or negative values)")
    return (exception_msg, stacktrace)


def run_duckdb(duckdb_cli, sql_statement):
    command = [duckdb_cli, '-batch', '-init', '/dev/null']
    timed_out = False
    try:
        res = subprocess.run(
            command, input=bytearray(sql_statement, 'utf8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5
        )
        stdout = res.stdout.decode('utf8', 'ignore').strip()
        stderr = res.stderr.decode('utf8', 'ignore').strip()
        returncode = res.returncode
    except subprocess.TimeoutExpired:
        return ("", "", 42, True)
    return (stdout, stderr, returncode, timed_out)


def reproduce_crashes(reproduction_dir, duckdb_cli, file_reader_function):
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
    for repro_item in reproduction_data:
        repro_file_path = reproduction_dir / 'crashes' / repro_item['file_name']
        arguments = ", " + repro_item['arguments'] if repro_item['arguments'] else ""
        exception_msg, stacktrace = reproduce_file_reader_issue(
            duckdb_cli, repro_file_path, file_reader_function, arguments
        )
        if exception_msg and exception_msg not in unique_crashes:
            unique_crashes[exception_msg] = (repro_file_path, arguments, exception_msg, stacktrace)
    return unique_crashes


def reproduce_hangs(reproduction_dir, duckdb_cli, file_reader_function):
    unique_hangs = {}
    # verify file _REPRODUCTIONS.json exists
    hangs_json_file = reproduction_dir / 'hangs/_REPRODUCTIONS.json'
    if not hangs_json_file.is_file():
        print(f"no hangs found; file not present: {hangs_json_file}")
        return unique_hangs
    with open(hangs_json_file, 'r') as repr_file_fd:
        reproduction_data: list = json.load(repr_file_fd)
    # verify REPRODUCTION_DIR contains the expected data files
    for repro_item in reproduction_data:
        repro_file_path = reproduction_dir / 'hangs' / repro_item['file_name']
        if not repro_file_path.is_file():
            raise ValueError(f"file not found: {repro_file_path}")
    # reproduce hangs (return as soon as 1 has been found)
    for repro_item in reproduction_data:
        print("looping over hangs ..")
        repro_file_path = reproduction_dir / 'hangs' / repro_item['file_name']
        arguments = ", " + repro_item['arguments'] if repro_item['arguments'] else ""
        exception_msg, stacktrace = reproduce_file_reader_issue(
            duckdb_cli, repro_file_path, file_reader_function, arguments
        )
        if exception_msg:
            unique_hangs[exception_msg] = (repro_file_path, arguments, exception_msg, stacktrace)
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
    duckdb_cli = DUCKDB_DIR / "build/debug/duckdb"
    if not duckdb_cli.is_file():
        raise ValueError(f"expected file not found: {duckdb_cli}")

    # reproduce crashes (keep unique crashes)
    unique_issues = reproduce_crashes(REPRODUCTION_DIR, duckdb_cli, file_reader_function)

    # reproduce hangs (keep max 1)
    unique_hangs = reproduce_hangs(REPRODUCTION_DIR, duckdb_cli, file_reader_function)
    unique_issues.update(unique_hangs)

    # only keep new issues
    new_issues = {}
    for issue in unique_issues.values():
        repro_file_path, arguments, exception_msg, stacktrace = issue
        title = exception_msg[:200]
        if not github_helper.is_known_github_issue(title):
            file_name_uuid = f"{time.strftime(r"%Y%m%d")}_{uuid.uuid4().hex[:6]}.{file_type}"
            rel_file_path = f"{file_type}/{file_name_uuid}"
            sql_statement_gh = f".sh wget {github_helper.file_url(rel_file_path)}\nfrom {file_reader_function}('{file_name_uuid}'{arguments});"
            new_issues[exception_msg] = (title, rel_file_path, repro_file_path, sql_statement_gh, exception_msg, stacktrace)

    # commit reproduction files
    if new_issues:
        run_command(f"mkdir -p {DUCKDB_FUZZER_DIR / file_type}")
        for issue in new_issues.values():
            title, rel_file_path, repro_file_path, sql_statement_gh, exception_msg, stacktrace = issue
            run_command(f"cp {repro_file_path} {DUCKDB_FUZZER_DIR / rel_file_path}")
        run_command(f"git -C {DUCKDB_FUZZER_DIR} add .")
        run_command(
            f"git -C {DUCKDB_FUZZER_DIR} commit -m 'add reproduction file for afl++ fuzz run {os.environ.get('FUZZ_RUN_ID')}'"
        )
        run_command(
            f"git -C {DUCKDB_FUZZER_DIR} push || (git -C {DUCKDB_FUZZER_DIR} config pull.rebase true && git -C {DUCKDB_FUZZER_DIR} pull git -C {DUCKDB_FUZZER_DIR} git push)"
        )

    # create github issues
    for issue in new_issues.values():
        title, rel_file_path, repro_file_path, sql_statement_gh, exception_msg, stacktrace = issue
        fuzzer_helper.file_issue(
            title, sql_statement_gh, exception_msg, stacktrace, os.environ['FUZZ_SCENARIO'], 0, os.environ['DUCKDB_SHA']
        )
        print(sql_statement_gh)


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
