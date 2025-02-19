#!/usr/bin/env python3

import github_helper
from pathlib import Path
import os

NUM_CRASHES = int(os.environ['NUM_CRASHES'])
NUM_HANGS = int(os.environ['NUM_HANGS'])

title = f"AFL++ run {os.environ['FUZZ_RUN_ID']}: crashes or hangs found for read_{os.environ['FILE_FORMAT']}() on: {os.environ['DUCKDB_SHA']}"

issue_desc = f"Issue found by {os.environ['FUZZ_SCENARIO']} for duckdb commit hash [{os.environ['DUCKDB_SHA']}](https://github.com/duckdb/duckdb/commit/{os.environ['DUCKDB_SHA']})\n\n"

fuzzer_desc = f"""### Fuzzer
fuzz scenrio: `{os.environ['FUZZ_SCENARIO']}`
triggered from: `{os.environ['FUZZ_REPO']}`
workflow: `{os.environ['FUZZ_WORKFLOW']}`
run_id: {os.environ['FUZZ_RUN_ID']} -> https://github.com/{os.environ['FUZZ_REPO']}/actions/runs/{os.environ['FUZZ_RUN_ID']}

duckdb ref: {os.environ['DUCKDB_REF']}
duckdb version: {os.environ['DUCKDB_VERSION']}
duckdb commit: {os.environ['DUCKDB_SHA']}

"""

summary = f"""### Summary
nr of crashes found: {NUM_CRASHES}
nr of hangs found: {NUM_HANGS}

"""


def main():
    reproduction = f"### Reproduction\n{"[CRASHES]" if NUM_CRASHES else ""}\n{"[HANGS]" if NUM_HANGS else ""}"
    if NUM_CRASHES:
        reproduction = set_reproduction_text("crashes", reproduction)
    if NUM_HANGS:
        reproduction = set_reproduction_text("hangs", reproduction)
    body = issue_desc + fuzzer_desc + summary + reproduction
    github_helper.make_github_issue(title, body)


def set_reproduction_text(crashes_or_hangs, reproduction_template):
    # paths
    reproduction_repo = "https://github.com/duckdb/duckdb-fuzzer/tree/main"
    reproduction_root_dir = os.environ['REPRODUCTION_DIR']
    match crashes_or_hangs:
        case 'crashes':
            sqllogic_filename = f"{os.environ['FUZZ_SCENARIO']}-{os.environ['DUCKDB_SHA']}.test"
            sqllogic_url = f"{reproduction_repo}/{reproduction_root_dir}/{sqllogic_filename}"
            reproduction_files_url = f"{reproduction_repo}/{reproduction_root_dir}/crashes"
            replace_str = "[CRASHES]"
        case 'hangs':
            sqllogic_filename = f"{os.environ['FUZZ_SCENARIO']}-{os.environ['DUCKDB_SHA']}-hangs.test"
            sqllogic_url = f"{reproduction_repo}/{reproduction_root_dir}/{sqllogic_filename}"
            reproduction_files_url = f"{reproduction_repo}/{reproduction_root_dir}/hangs"
            replace_str = "[HANGS]"
        case _:
            raise ValueError(f"invalid input: {crashes_or_hangs}")

    reproduction_text = f"""reproduction files for {crashes_or_hangs} in `read_{os.environ['FILE_FORMAT']}`:
- failing sqllogic tests: {sqllogic_url}
- data files: {reproduction_files_url}

"""
    return reproduction_template.replace(replace_str, reproduction_text)


if __name__ == "__main__":
    if not(NUM_CRASHES or NUM_HANGS):
        print("no crashes or hangs to register")
        exit(0)
    main()
