#!/usr/bin/env python3

'''
Script to reproduce the crashes when using function 'read_json' (found by: json_file_parameter_flex_fuzzer)
The script takes the following inputs:
- a directory 'REPRODUCTION_DIR' with problematic json files
- file _REPRODUCTIONS.json, which lists the parameters for read_json() per file to use to reproduce the issues
'''

from pathlib import Path
import io
import json
import subprocess

# duckdb should be compiled with: BUILD_JSON=1 CRASH_ON_ASSERT=1 BUILD_JEMALLOC=1
DUCKDB_PATH = Path("~/git/duckdb/build/release/duckdb").expanduser()

# inputs:
REPRODUCTION_DIR = Path("~/Desktop/reproductions").expanduser()
REPRODUCTION_JSON = REPRODUCTION_DIR / "_REPRODUCTIONS.json"

# output:
REPRODUCTION_LOG = REPRODUCTION_DIR / "_reproductions.log"

ANSI_RESET = "\033[0m"
ANSI_RED = "\033[91m"
ANSI_GREEN = "\033[92m"


def main():
    count_success = 0
    count_regular_errors = 0
    count_internal_errors = 0
    count_crashing_errors = 0
    count_total = 0

    cases = get_test_cases()
    logfile: Path = Path(REPRODUCTION_LOG)
    if logfile.is_file():
        logfile.unlink()
    fd_log = logfile.open(mode='a')

    for case in cases:
        argument_str = case['arguments']
        case_file: Path = REPRODUCTION_DIR / case['file_name']
        # try to reproduce without extra arguments
        res = subprocess.run(
            f"{DUCKDB_PATH} -c \"select * from read_json('{case_file}');\"", shell=True, capture_output=True
        )
        if res.returncode == 0 or res.returncode == 1:
            # try to reproduce with extra arguments
            res = subprocess.run(
                f"{DUCKDB_PATH} -c \"select * from read_json('{case_file}', {argument_str});\"",
                shell=True,
                capture_output=True,
            )
        if res.returncode == 0:
            count_success += 1
        elif res.returncode == 1:
            count_regular_errors += 1
        elif res.stderr:
            count_internal_errors += 1
        else:
            count_crashing_errors += 1
        count_total += 1
        create_logging(fd_log, res, case_file)

    fd_log.close()

    # print summary
    print(f"{count_total} - scenarios executed")
    print(f"{ANSI_GREEN}{count_success}{ANSI_RESET} - scenarios with exit status 0 (OK)")
    print(f"{ANSI_GREEN}{count_regular_errors}{ANSI_RESET} - scenarios with exit status 1 (Regular Error, assuming duckdb is compiled with CRASH_ON_ASSERT)")
    print(f"{ANSI_RED}{count_internal_errors}{ANSI_RESET} - scenarios with other exit status (Internal Exception / Assertion Error)")
    print(f"{ANSI_RED}{count_crashing_errors}{ANSI_RESET} - scenarios with crash")
    print(f"for details, see: {REPRODUCTION_LOG}")


def get_test_cases() -> list[dict]:
    if not Path(REPRODUCTION_DIR).is_dir():
        print(f"Error Directory not found: {REPRODUCTION_DIR}")
        exit(1)
    cases: list[dict] = json.loads(REPRODUCTION_JSON.read_text())
    for case in cases:
        if 'file_name' not in case or 'arguments' not in case:
            print(f"Error: ill formatted json file: {REPRODUCTION_JSON}")
            exit(1)
        case_file: Path = REPRODUCTION_DIR / case['file_name']
        if not case_file.is_file():
            print(f"Error: file not found: {case_file}")
            exit(1)
    return cases


def create_logging(fd_log: io.TextIOWrapper, res: subprocess.CompletedProcess, case_file: Path):
    fd_log.write(f"{case_file}\n")
    fd_log.write(f"{res.args}\n")
    fd_log.write(f"{res.returncode}\n")
    if res.returncode != 0 and res.returncode != 1:
        if not res.stderr.decode():
            fd_log.write(f"CRASH!\n")
        else:
            fd_log.write(f"{res.stderr.decode()}")
    fd_log.write(f"\n\n")


if __name__ == "__main__":
    main()
