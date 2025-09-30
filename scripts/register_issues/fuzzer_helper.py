import subprocess
import re

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

def extract_issue(body, nr):
    try:
        if trace_header in body:
            sql = body.split(sql_header)[1].split(exception_header)[0]
            error = body.split(exception_header)[1].split(trace_header)[0]
            trace = body.split(trace_header)[1].split(footer)[0]
        else:
            splits = body.split(exception_header)
            sql = splits[0].split(sql_header)[1]
            error = splits[1][: -len(footer)]
            trace = ""
        return (sql, error, trace)
    except:
        print(f"Failed to extract SQL/error message from issue {nr}")
        print(body)
        return None


def run_shell_command_batch(shell, cmd):
    command = [shell, '--batch', '-init', '/dev/null']

    try:
        res = subprocess.run(
            command, input=bytearray(cmd, 'utf8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300
        )
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT... {cmd}")
        return ("", "", 0, True)
    stdout = res.stdout.decode('utf8').strip()
    stderr = res.stderr.decode('utf8').strip()
    return (stdout, stderr, res.returncode, False)


def is_reproducible_issue(shell, issue) -> bool:
    if any(label['name'] == 'AFL' for label in issue['labels']):
        # The reproducibility of AFL issues can not be tested, because they are formatted differently.
        # We assume they are reproducible (i.e. not fixed yet)
        return True
    extract = extract_issue(issue['body'], issue['number'])
    labels = issue['labels']
    label_timeout = False
    for label in labels:
        if label['name'] == 'timeout':
            label_timeout = True
    if extract is None:
        # failed extract: leave the issue as-is
        return True
    sql = extract[0] + ';'
    if label_timeout is False:
        print(f"Checking issue {issue['number']}...")
        (stdout, stderr, returncode, is_timeout) = run_shell_command_batch(shell, sql)
        if is_timeout:
            github_helper.label_github_issue(issue['number'], 'timeout')
        else:
            if returncode == 0:
                return False
            if not is_internal_error(stderr):
                return False
    # issue is still reproducible
    return True


# closes non-reproducible issues; returns reproducible issues
def close_non_reproducible_issues(shell) -> dict[str, dict]:
    reproducible_issues: dict[str, dict] = {}
    for issue in github_helper.get_github_issues_list():
        if not is_reproducible_issue(shell, issue):
            # the issue appears to be fixed - close the issue
            print(f"Failed to reproduce issue {issue['number']}, closing...")
            github_helper.close_github_issue(int(issue['number']))
        else:
            reproducible_issues[issue['title']] = issue
    # retun open issues as dict, so they can be searched by title, which is the exception message without trace
    return reproducible_issues


def file_issue(title, sql_statement, exception_msg, stacktrace, fuzzer, seed, hash):
    # issue is new, file it
    body = (
        fuzzer_desc.replace("${FUZZER}", fuzzer)
        .replace("${FULL_HASH}", hash)
        .replace("${SHORT_HASH}", hash[:5])
        .replace("${SEED}", str(seed))
    )
    body += sql_header + sql_statement + exception_header + exception_msg + trace_header + stacktrace + footer
    print(title, body)
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
    err = re.sub(r'../duckdb\((.*)\)', r'\1', err)
    err = re.sub(r'[\+\[]?0x[0-9a-fA-F]+\]?', '', err)
    err = re.sub(r'/lib/x86_64-linux-gnu/libc.so(.*)\n', '', err)
    return err.strip()


def split_exception_trace(exception_msg_full: str) -> tuple[str, str]:
    # exception message does not contain newline, so split after first newline
    exception_msg, _, stack_trace = exception_msg_full.partition('\n')
    # if first line only contains =-symbols, skip it
    if(re.fullmatch("=*", exception_msg)):
        exception_msg, _, stack_trace = stack_trace.partition('\n')
    return (exception_msg.strip(), sanitize_stacktrace(stack_trace))
