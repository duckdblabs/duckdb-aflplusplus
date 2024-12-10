#!/usr/bin/env python3

'''
This script scrapes occurences of 'read_csv()' from the test directory, and stores them in a JSON-file
The created json can be used as input for fuzzing the read_csv() function
'''

import json
from pathlib import Path

FILE_DIR_TO_SCRAPE = Path('~/git/duckdb/test/').expanduser()
CSV_CORPUS_JSON = Path(__file__).parents[1] / 'corpus/csv/csv_parameter.json'


def main():
    all_test_files = FILE_DIR_TO_SCRAPE.rglob('*')
    file_reader_expressions = []
    scenario_id = 0

    for test_file in all_test_files:
        if not test_file.is_file():
            continue
        try:
            file_content = test_file.read_text()
        except UnicodeDecodeError:
            # skip for now: non-unicode files
            continue
        for read_csv_expression in find_function_expressions(file_content, 'read_csv'):
            file_and_argument_str = read_csv_expression.partition('read_csv(')[2].rpartition(')')[0]
            expression_obj = create_file_reader_dict(file_and_argument_str, scenario_id)
            if expression_obj:
                file_reader_expressions.append(expression_obj)
                scenario_id += 1

    # write file
    CSV_CORPUS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with CSV_CORPUS_JSON.open('w') as csv_corpus_json:
        json.dump(file_reader_expressions, csv_corpus_json, indent=4)


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
                    argument_list.append(argument_string[start_idx:idx])
                    start_idx = idx + 1
        idx += 1
    return argument_list


if __name__ == '__main__':
    main()
