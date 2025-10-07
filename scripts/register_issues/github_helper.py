import json
import requests
import re
import os
import urllib.parse

USERNAME = 'fuzzerofducks'

REPO_OWNER = 'duckdb'
REPO_NAME = 'duckdb-fuzzer'


# functions borrowed from duckdb/duckdb_sqlsmith -> fuzzer_helper.py


def issue_url():
    return 'https://api.github.com/repos/%s/%s/issues' % (REPO_OWNER, REPO_NAME)


def file_url(file_path):
    return f"https://github.com/{REPO_OWNER}/{REPO_NAME}/raw/refs/heads/main/{file_path}"


def get_token():
    if 'FUZZEROFDUCKSKEY' not in os.environ:
        print("FUZZEROFDUCKSKEY not found in environment variables")
        exit(1)
    token = os.environ['FUZZEROFDUCKSKEY']
    if len(token) == 0:
        print("FUZZEROFDUCKSKEY is set but is empty")
        exit(1)
    if len(token) != 40:
        print("Incorrect length for FUZZEROFDUCKSKEY")
        exit(1)
    return token


def create_session():
    # Create an authenticated session to create the issue
    session = requests.Session()
    session.headers.update({'Authorization': 'token %s' % (get_token(),)})
    return session


def make_github_issue(title, body, labels=[]):
    if len(title) > 240:
        #  avoid title is too long error (maximum is 256 characters)
        title = title[:240] + '...'
    if len(body) > 60000:
        body = body[:60000] + '... (body of github issue is truncated)'
    session = create_session()
    url = issue_url()
    issue = {'title': title, 'body': body, 'labels': labels}
    r = session.post(url, json.dumps(issue))
    if r.status_code == 201:
        print('Successfully created Issue "%s"' % title)
        issue_json = r.json()
        print(f"::notice::created issue: {issue_json.get('html_url')} - {issue_json.get('title')}")
    else:
        print('Could not create Issue "%s"' % title)
        print('Response:', r.content.decode('utf8'))
        raise Exception("Failed to create issue")


def issues_by_title_url(*title_parts):
    base_url = "https://api.github.com/search/issues"
    title_str = " ".join(title_part for title_part in title_parts)
    query_string = urllib.parse.quote(f"repo:{REPO_OWNER}/{REPO_NAME} {title_str} in:title is:open")
    return f"{base_url}?q={query_string}"


def get_github_issues_by_title(*issue_title) -> list[dict]:
    session = create_session()
    url = issues_by_title_url(*issue_title)
    r = session.get(url)
    if r.status_code != 200:
        print('Failed to query the issues')
        print('Response:', r.content.decode('utf8'))
        raise Exception("Failed to query the issues")
    issue_list = r.json().get("items", [])
    return issue_list


def is_known_github_issue(exception_msg):
    # search for combination of title parts, strip some numbers, to prevent near-duplicates
    title_parts = re.split(r" \d+", exception_msg)
    existing_issues = get_github_issues_by_title(*tuple(title_parts))
    if existing_issues:
        print("Skip filing duplicate issue")
        print(
            f"Issue already exists: https://github.com/{REPO_OWNER}/{REPO_NAME}/issues/"
            + str(existing_issues[0]['number'])
        )
        return True
    else:
        return False
