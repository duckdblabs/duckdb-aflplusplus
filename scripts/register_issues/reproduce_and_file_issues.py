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
    if(re.fullmatch("=*", exception_msg)):
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


def run_duckdb(duckdb_cli, sql_statement):
    command = [duckdb_cli, '-batch', '-init', '/dev/null']
    res = subprocess.run(command, input=bytearray(sql_statement, 'utf8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = res.stdout.decode('utf8', 'ignore').strip()
    stderr = res.stderr.decode('utf8', 'ignore').strip()
    return (stdout, stderr, res.returncode)


def main(argv: list[str]):
    file_reader_function = argv[1]  # read_csv / read_json / read_parquet
    match file_reader_function:
        case 'read_csv':
            file_type = 'csv'
        case 'read_json':
            file_type = 'json'
        case 'read_parquet':
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

    # issue_file_dir = DUCKDB_FUZZER_DIR / f"issue_files/{file_type}"

    # verify file _REPRODUCTIONS.json exists
    reproductions_json_file = REPRODUCTION_DIR / 'crashes/_REPRODUCTIONS.json'
    if not reproductions_json_file.is_file():
        raise ValueError(f"expected file not found: {reproductions_json_file}")
    with open(reproductions_json_file, 'r') as repr_file_fd:
        reproduction_data: list = json.load(repr_file_fd)

    # verify REPRODUCTION_DIR contains the expected data files
    for repro_item in reproduction_data:
        repro_file_path = REPRODUCTION_DIR / 'crashes' / repro_item['file_name']
        if not repro_file_path.is_file():
            raise ValueError(f"file not found: {repro_file_path}")

    # verify duckdb_cli can be found
    duckdb_cli = DUCKDB_DIR / "build/debug/duckdb"
    if not duckdb_cli.is_file():
        raise ValueError(f"expected file not found: {duckdb_cli}")

    # reproduce crashes
    unique_issues = {}
    for repro_item in reproduction_data:
        repro_file_path = REPRODUCTION_DIR / 'crashes' / repro_item['file_name']
        arguments = ", " + repro_item['arguments'] if repro_item['arguments'] else ""
        sql_statement = f"from {file_reader_function}('{repro_file_path}'{arguments})"
        (stdout, stderr, returncode) = run_duckdb(duckdb_cli, sql_statement)

        match returncode:
            case 0:
                continue
            case 1 if not is_internal_error(stderr):
                continue
            case 1:
                exception_msg, stacktrace = split_exception_trace(stderr)
            case _ if returncode < 0:
                exception_msg, stacktrace = split_exception_trace(stderr)
                sig_name = signal.Signals(-returncode).name
                exception_msg = f"{sig_name}: {exception_msg}"
            case _:
                raise ValueError(f"undefined return code: {returncode} (expected 0, 1, or negative values)")
        if exception_msg not in unique_issues:
            unique_issues[exception_msg] = (repro_file_path, arguments, exception_msg, stacktrace)

    # only keep new issues
    new_issues = {}
    for issue in unique_issues.values():
        repro_file_path, arguments, exception_msg, stacktrace = issue
        title = exception_msg[:200]
        if not github_helper.is_known_github_issue(title):
            file_name_uuid = f"{time.strftime(r"%Y%m%d")}_{uuid.uuid4().hex[:6]}.{file_type}"
            rel_file_path = f"{file_type}/{file_name_uuid}"
            sql_statement_gh = f".sh wget {github_helper.file_url(rel_file_path)}; from {file_reader_function}('{file_name_uuid}'{arguments});"
            new_issues[exception_msg] = (title, rel_file_path, repro_file_path, sql_statement_gh, exception_msg, stacktrace)

    # commit reproduction files
    if new_issues:
        run_command(f"mkdir -p {DUCKDB_FUZZER_DIR / file_type}")
        for issue in new_issues.values():
            title, rel_file_path, repro_file_path, sql_statement_gh, exception_msg, stacktrace = issue
            run_command(f"cp {repro_file_path} {DUCKDB_FUZZER_DIR / rel_file_path}")
        run_command(f"git -C {DUCKDB_FUZZER_DIR} add .")
        run_command(f"git -C {DUCKDB_FUZZER_DIR} commit -m 'add reproduction file for afl++ fuzz run {os.environ.get('FUZZ_RUN_ID')}'")
        run_command(f"git -C {DUCKDB_FUZZER_DIR} push || (git -C {DUCKDB_FUZZER_DIR} config pull.rebase true && git -C {DUCKDB_FUZZER_DIR} pull git -C {DUCKDB_FUZZER_DIR} git push)")

    # create github issues
    for issue in new_issues.values():
        title, rel_file_path, repro_file_path, sql_statement_gh, exception_msg, stacktrace = issue
        fuzzer_helper.file_issue(title, sql_statement_gh, exception_msg, stacktrace, os.environ['FUZZ_SCENARIO'], 0, os.environ['DUCKDB_SHA'])
        print(sql_statement_gh)


if __name__ == "__main__":
    if len(sys.argv) not in range(2, 5):
        sys.exit(
            """
            ERROR; call this script with the following arguments:
              1 - target function ('read_csv', 'read_json' or 'read_parquet')
              2 - (optional) path to reproductions directory (created by decode_multi_param_files.py)
              3 - (optional) path to duckdb directory
              4 - (optional) path to /duckdb/duckdb-fuzzer directory
            """
        )
    main(sys.argv)
