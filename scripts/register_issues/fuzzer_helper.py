import os
import re
import signal
import subprocess
from pathlib import Path

import github_helper

# functions borrowed from duckdb/duckdb_sqlsmith -> fuzzer_helper.py

fuzzer_desc = '''Issue found by ${FUZZER} on git commit hash [${SHORT_HASH}](https://github.com/duckdb/duckdb/commit/${FULL_HASH}) using seed ${SEED}.
'''

sql_header = '''### To Reproduce
```sql
'''

exception_header = '''
```

### Error Message
```
'''

trace_header = '''
```

### Stack Trace
```
'''

footer = '''
```'''


def file_issue(title, sql_statement, exception_msg, stacktrace, fuzzer, seed, hash):
    # issue is new, file it
    body = (
        fuzzer_desc.replace("${FUZZER}", fuzzer)
        .replace("${FULL_HASH}", hash)
        .replace("${SHORT_HASH}", hash[:5])
        .replace("${SEED}", str(seed))
    )
    body += sql_header + sql_statement + exception_header + exception_msg + trace_header + stacktrace + footer
    github_helper.make_github_issue(title, body)


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
        exception_msg = "AddressSanitizer: heap-buffer-overflow; " + '\n'.join(trace_lines[:2])
    return (exception_msg.strip(), stack_trace)


def run_command(command):
    res = os.system(command)
    if res != 0:
        print(f"command '{command}' failed with exit code: {res}")
        exit(res)


def print_std_error(duckdb_cli, sql_statement, stderr):
    print("\n==== duckdb_cli: ===")
    print(duckdb_cli)
    print("\n==== sql_statement: ===")
    print(sql_statement)
    print("\n==== STD error: ===")
    print(stderr)
    print("==========", flush=True)


def run_sql(duckdb_cli, sql_statement, fuzzer_name) -> tuple[str, str]:
    (stdout, stderr, returncode, timed_out) = run_duckdb(duckdb_cli, sql_statement)
    match returncode:
        case 0:
            exception_msg, stacktrace = "", ""
        case 1 if not is_internal_error(stderr):  # regular error
            exception_msg, stacktrace = "", ""
        case 1:  # internal error
            print_std_error(duckdb_cli, sql_statement, stderr)
            exception_msg, stacktrace = split_exception_trace(stderr)
        case _ if returncode < 0:  # crash
            print_std_error(duckdb_cli, sql_statement, stderr)
            exception_msg, stacktrace = split_exception_trace(stderr)
            sig_name = signal.Signals(-returncode).name
            exception_msg = f"{sig_name}: {exception_msg}"
        case _ if timed_out:  # hang
            exception_msg, stacktrace = (f"{fuzzer_name} timed out after 300 s", "")
        case _:
            raise ValueError(f"undefined return code: {returncode} (expected 0, 1, or negative values)")
    return (exception_msg, stacktrace)


def reproduce_filereader_issue(duckdb_cli, repro_file_path, file_reader_function, arguments):
    sql_statement = f"from {file_reader_function}('{repro_file_path}'{arguments})"
    exception_msg, stacktrace = run_sql(duckdb_cli, sql_statement, file_reader_function)
    return (exception_msg, stacktrace)


def reproduce_crashes_from_sql_dir(sql_file_dir: Path, duckdb_cli: Path, max_one=False):
    unique_crashes = {}
    all_sql_files = sorted(sql_file_dir.iterdir())
    print(f"reproducing errors in {len(all_sql_files)} sql files in dir {sql_file_dir} ...")
    for sql_file in all_sql_files:
        sql_statement = sql_file.read_text()
        exception_msg, stacktrace = run_sql(duckdb_cli, sql_statement, 'sql_fuzzer')
        if exception_msg:
            unique_crashes[exception_msg] = (sql_statement, exception_msg, stacktrace)
            if max_one:
                break
    return unique_crashes


def run_duckdb(duckdb_cli, sql_statement):
    command = [duckdb_cli, '-batch', '-init', '/dev/null']
    timed_out = False
    try:
        res = subprocess.run(
            command, input=bytearray(sql_statement, 'utf8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300
        )
        stdout = res.stdout.decode('utf8', 'ignore').strip()
        stderr = res.stderr.decode('utf8', 'ignore').strip()
        returncode = res.returncode
    except subprocess.TimeoutExpired:
        return ("", "", 42, True)
    return (stdout, stderr, returncode, timed_out)
