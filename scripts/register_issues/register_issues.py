#!/usr/bin/env python3

import github_helper
from pathlib import Path
import os

def main():
    title = 'dummy AFL++ issue'
    body = 'This is a dummy issue to test if the permissions work correctly to create issues from duckdb_aflplusplus.\nFeel free to close this issue.'
    # github_helper.make_github_issue(title, body)

    # debug validate token
    print("validate token..")
    github_helper.get_token()
    print("ok..")

    crashes_dir = Path('./reproductions/crashes')
    hangs_dir = Path('./reproductions/hangs')
    sqllogic_test_crahses = Path('13288614425-csv_multi_param_fuzzer.test')
    sqllogic_test_hangs = Path('13288614425-csv_multi_param_fuzzer.test')

    print(f"fuzz run id {os.environ['FUZZ_RUN_ID']}")
    print(sqllogic_test_crahses.read_text())

if __name__ == "__main__":
    main()
