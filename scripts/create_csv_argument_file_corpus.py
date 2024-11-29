#!/usr/bin/env python3

'''
This script scrapes occurences of 'read_csv()' from the test directory, and stores them in a JSON-file
The created json can be used as input for fuzzing the read_csv() function
'''

import json
import re
from pathlib import Path

FILE_DIR = Path('~/git/duckdb/test/').expanduser()
CSV_CORPUS_JSON = Path(__file__).parents[1] / 'corpus/csv/csv_parameter.json'


def main():
    all_test_files = FILE_DIR.rglob("*")
    file_reader_expressions = []

    for test_file in all_test_files:
        if not test_file.is_file():
            continue
        try:
            file_content = test_file.read_text()
        except UnicodeDecodeError:
            # skip for now: non-unicode files
            continue
        for read_csv_expression in find_function_expression(file_content, 'read_csv'):
            file_and_argument_str = read_csv_expression.partition("read_csv(")[2].rpartition(")")[0]
            expression_obj = create_file_reader_dict(file_and_argument_str)
            if expression_obj:
                file_reader_expressions.append(expression_obj)

    # write file
    CSV_CORPUS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with CSV_CORPUS_JSON.open('w') as csv_corpus_json:
        json.dump(file_reader_expressions, csv_corpus_json)


# returns a list of function calls found in a text
# follows the sting up to the correct closing parenthesis
def find_function_expression(text: str, function_str: str) -> list[str]:
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


def create_file_reader_dict(file_and_argument_str: str) -> dict | None:
    if file_and_argument_str[0] == "[":
        # skip for now: multiple files
        return None
    file_name, _, arguments = file_and_argument_str.partition(",")
    if not arguments or '*' in file_name:
        # skip for now: no arguments or wildcard in filename
        return None
    file_name = file_name.strip().replace("'", "").replace("\"", "")
    arguments = arguments.strip()
    if file_name[0:4] != 'data':
        # skip for now: reads from exteneral sources
        return None
    return dict(
        {
            "arguments": dict(
                {
                    (lambda x: (x[0].strip(), x[2].strip()))(arg.partition('='))
                    for arg in split_argument_string(arguments)
                }
            ),
            "data_file": file_name,
        }
    )


# split by comma, except commas within quotes, or parentheses: "" '' [] () {}
def split_argument_string(argument_string):
    # Temporarily replace non-splitting commas by placeholder byte, so we can safely split
    placeholder = '\x01'
    argument_string = re.sub(
        r'("(?:.|\n)*?")|(\'(?:.|\n)*?\')|(\[(?:.|\n)*?\])|(\((?:.|\n)*?\))|(\{(?:.|\n)*?\})',
        lambda m: m.group(0).replace(',', placeholder),
        argument_string,
    )
    argument_list = argument_string.split(',')
    argument_list = [argument.replace(placeholder, ',') for argument in argument_list]
    return argument_list


if __name__ == "__main__":
    main()
