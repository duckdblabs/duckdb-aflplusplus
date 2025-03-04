import json
import requests
import os

USERNAME = 'fuzzerofducks'

REPO_OWNER = 'duckdb'
REPO_NAME = 'duckdb-fuzzer'


# github stuff
# functions borrowed from duckdb/duckdb_sqlsmith -> fuzzer_helper.py
def issue_url():
    return 'https://api.github.com/repos/%s/%s/issues' % (REPO_OWNER, REPO_NAME)


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
