import github_helper

def main():
    title = 'dummy AFL++ issue'
    body = 'This is a dummy issue to test if the permissions work correctly to create issues from duckdb_aflplusplus.\nFeel free to close this issue.'
    github_helper.make_github_issue(title, body)

if __name__ == "__main__":
    main()
