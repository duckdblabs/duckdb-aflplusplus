#!/usr/bin/env python3

'''
This script scrapes occurences of function calls (read_csv, read_json, read_parquet)
from the test directory, and stores them in a JSON-file
The created json can be used as input for script 'create_multi_param_corpus.py'
'''

import duckdb
import json
import sys
from pathlib import Path

FILE_DIR_TO_SCRAPE = Path('~/git/duckdb/test/').expanduser()
DUCKDB_DIR = Path('~/git/duckdb/').expanduser()
CSV_CORPUS_JSON = Path(__file__).parents[2] / 'corpus/csv/csv_parameter.json'
JSON_CORPUS_JSON = Path(__file__).parents[2] / 'corpus/json/json_parameter.json'
PARQUET_CORPUS_JSON = Path(__file__).parents[2] / 'corpus/parquet/parquet_parameter.json'


def main(argv: list):
    function_to_scrape = argv[1]
    match function_to_scrape:
        case 'read_csv':
            corpus_json_path = CSV_CORPUS_JSON
            functions_to_scrape = ['read_csv', 'read_csv_auto']
        case 'read_json':
            corpus_json_path = JSON_CORPUS_JSON
            functions_to_scrape = ['read_json', 'read_json_auto']
        case 'read_parquet':
            corpus_json_path = PARQUET_CORPUS_JSON
            functions_to_scrape = ['read_parquet']
        case _:
            raise ValueError(f"invalid input: {function_to_scrape}")

    all_test_files = FILE_DIR_TO_SCRAPE.rglob('*')
    function_expressions = []
    scenario_id = 0

    for test_file in all_test_files:
        if not test_file.is_file():
            continue
        try:
            file_content = test_file.read_text()
        except UnicodeDecodeError:
            # skip for now: non-unicode files
            continue
        for func in functions_to_scrape:
            for expression in find_function_expressions(file_content, func):
                file_and_argument_str = expression.partition(f'{func}(')[2].rpartition(')')[0]
                expression_obj = create_file_reader_dict(file_and_argument_str, scenario_id)
                if expression_obj:
                    function_expressions.append(expression_obj)
                    scenario_id += 1

    # write file
    corpus_json_path.parent.mkdir(parents=True, exist_ok=True)
    with corpus_json_path.open('w') as corpus_json:
        json.dump(function_expressions, corpus_json, indent=4)

    # prune with duckdb, keep 1 record per data_file
    if len(function_expressions) > 100:
        prune_corpus_json(corpus_json_path.absolute())


# returns a list of function calls found in a text
# follows the sting up to the correct closing parenthesis
def find_function_expressions(text: str, function_str: str) -> list[str]:
    if function_str[-1:] != '(':
        function_str += '('
    found_expressions = []
    idx = 0
    while idx < len(text):
        idx = text.find(function_str, idx)
        if idx == -1:
            break
        start_idx = idx
        nr_open_parentheses = 0
        while idx < len(text):
            if text[idx] == '(':
                nr_open_parentheses += 1
            if text[idx] == ')':
                nr_open_parentheses -= 1
            if (nr_open_parentheses == 0 and text[idx] == ')') or nr_open_parentheses < 0:
                found_expressions.append(text[start_idx : idx + 1])
                break
            idx += 1
    return found_expressions


def create_file_reader_dict(file_and_argument_str: str, scenario_id: int) -> dict | None:
    if file_and_argument_str[0] == '[':
        # skip for now: multiple files
        return None
    file_name, _, arguments = file_and_argument_str.partition(',')
    if not arguments or any(char in file_name for char in '*[]'):
        # skip for now: no arguments or filename with wildcard or option ranges, e.g. [0-9]
        return None
    file_name = file_name.replace('\'', '').replace('\"', '').strip()
    arguments = arguments.strip()
    if file_name[0:4] != 'data':
        # skip for now: reads from exteneral sources
        return None
    if not (DUCKDB_DIR / file_name).exists():
        # skip: file not found
        return None
    scenario_dict = {'id': scenario_id}
    scenario_dict['data_file'] = file_name
    scenario_dict['arguments'] = dict(
        {
            (lambda x: (clean_parameter_name(x[0]), x[2].strip()))(arg.partition('='))
            for arg in split_argument_string(arguments)
        }
    )
    return scenario_dict


def clean_parameter_name(parameter_str: str) -> str:
    parameter_str = parameter_str.strip()
    if parameter_str[-1] == ':':
        parameter_str = parameter_str[:-1].strip()
    return parameter_str.lower()


# split on comma, but only when not within quotes or parentheses: "" '' [] () {}
def split_argument_string(argument_string):
    # 'stack' opening parentheses: [ ( { and quotes: ' " in a string to keep track of the nesting
    # note that quotes can only occur at the top
    state_stack = ''

    argument_list = []
    idx = 0
    start_idx = 0
    while idx < len(argument_string):
        state_char = state_stack[-1] if state_stack else None
        char = argument_string[idx]

        # last char: add tail end
        if idx == len(argument_string) - 1 and char != ',':
            argument_list.append(argument_string[start_idx:])
            break
        if char not in ['\"', '\'', '[', ']', '(', ')', '{', '}', ',']:
            # no special char: do nothing
            idx += 1
            continue
        if state_char in ['\"', '\''] and char != state_char:
            # inside of quotes, and not closing them yet: do nothing
            idx += 1
            continue

        match char:
            case '\"' | '\'':
                if char != state_char:
                    state_stack = state_stack + char
                else:
                    state_stack = state_stack[:-1]
            case '[' | '(' | '{':
                state_stack = state_stack + char
            case ']' | ')' | '}':
                assert (
                    (state_char == '[' and char == ']')
                    or (state_char == '(' and char == ')')
                    or (state_char == '{' and char == '}')
                )
                state_stack = state_stack[:-1]
            case ',':
                if not state_stack:
                    # split on comma, we are not within quotes or parentheses
                    argument_list.append(argument_string[start_idx:idx])
                    start_idx = idx + 1
        idx += 1
    return argument_list


# prune with duckdb, keep 1 record per data_file
def prune_corpus_json(corpus_json_full_path: str) -> None:
    query = f"""
    copy (
    select
        row_number() OVER () id,
        data_file,
        max(arguments) as arguments
    from
        read_json ('{corpus_json_full_path}', map_inference_threshold=5)
    group by
        data_file,
    order by
        all
    ) to '{corpus_json_full_path}' (array true);
    """
    duckdb.sql(query)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(
            "ERROR. provide the target function to scrape ('read_csv', 'read_json' or 'read_parquet') as first argument"
        )
    main(sys.argv)
