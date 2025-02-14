#!/usr/bin/env python3

import github_helper

def main():
    title = 'dummy AFL++ issue'
    body = 'This is a dummy issue to test if the permissions work correctly to create issues from duckdb_aflplusplus.\nFeel free to close this issue.'
    # github_helper.make_github_issue(title, body)

    # debug validate token
    print("validate token..")
    github_helper.get_token()
    print("ok..")

if __name__ == "__main__":
    main()
