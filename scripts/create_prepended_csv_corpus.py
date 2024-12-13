#!/usr/bin/env python3

'''
This script creates a csv fuzz corpus by prepending the parameter info to the csv data.
The input 'CSV_CORPUS_JSON' is created by script 'create_file_corpus_json.py'
'''

import json
import shutil
from pathlib import Path

CSV_CORPUS_ROOT_DIR = Path(__file__).parents[1] / 'corpus/csv/'
CSV_CORPUS_JSON = CSV_CORPUS_ROOT_DIR / 'csv_parameter.json'
OUT_DIR = CSV_CORPUS_ROOT_DIR / 'corpus_prepended'
DUCKDB_DIR = FILE_DIR_TO_SCRAPE = Path('~/git/duckdb/').expanduser()

# NOTE: keep this list in sync with 'src/csv_parameters.cpp' !!
# NOTE: types here are simplified to 'BOOLEAN', 'INTEGER', and 'VARCHAR'
# VARCHAR is also used for all complex types (lists, structs, etc)
READ_CSV_PARAMETERS = [
    ("all_varchar", "BOOLEAN"),
    ("allow_quoted_nulls", "BOOLEAN"),
    ("auto_detect", "BOOLEAN"),
    ("auto_type_candidates", "VARCHAR"),
    ("columns", "VARCHAR"),
    ("compression", "VARCHAR"),
    ("dateformat", "VARCHAR"),
    ("decimal_separator", "VARCHAR"),
    ("delim", "VARCHAR"),
    ("delimiter", "VARCHAR"),
    ("dtypes", "VARCHAR"),
    ("escape", "VARCHAR"),
    ("filename", "BOOLEAN"),
    ("force_not_null", "VARCHAR"),
    ("header", "BOOLEAN"),
    ("hive_partitioning", "BOOLEAN"),
    ("ignore_errors", "BOOLEAN"),
    ("max_line_size", "INTEGER"),
    ("names", "VARCHAR"),
    ("new_line", "VARCHAR"),
    ("normalize_names", "BOOLEAN"),
    ("null_padding", "BOOLEAN"),
    ("nullstr", "VARCHAR"),
    ("parallel", "BOOLEAN"),
    ("quote", "VARCHAR"),
    ("sample_size", "INTEGER"),
    ("sep", "VARCHAR"),
    ("skip", "INTEGER"),
    ("timestampformat", "VARCHAR"),
    ("types", "VARCHAR"),
    ("union_by_name", "BOOLEAN"),

    # undocumented
    ("buffer_size", "INTEGER"),
    ("column_names", "VARCHAR"),
    ("column_types", "VARCHAR"),
    ("comment", "VARCHAR"),
    ("date_format", "VARCHAR"),
    ("encoding", "VARCHAR"),
    ("force_quote", "VARCHAR"),
    ("hive_type", "VARCHAR"),
    ("hive_type_autocast", "BOOLEAN"),
    ("hive_types", "VARCHAR"),
    ("hive_types_autocast", "BOOLEAN"),
    ("maximum_line_size", "INTEGER"),
    ("null", "VARCHAR"),
    ("prefix", "VARCHAR"),
    ("rejects_limit", "INTEGER"),
    ("rejects_scan", "VARCHAR"),
    ("rejects_table", "VARCHAR"),
    ("rfc_4180", "BOOLEAN"),
    ("store_rejects", "BOOLEAN"),
    ("suffix", "VARCHAR"),
    ("timestamp_format", "VARCHAR"),
]

READ_CSV_PARAMETERS_DICT = {param[0]: (param_idx, param[1]) for param_idx, param in enumerate(READ_CSV_PARAMETERS)}


def main():
    if not CSV_CORPUS_JSON.exists():
        print(f"file not found: {CSV_CORPUS_JSON}")
        exit(1)
    file_content = CSV_CORPUS_JSON.read_text()
    scenario_list = json.loads(file_content)
    nr_corpus_files_created = 0
    nr_rejcts_arg_too_long = 0
    nr_rejcts_csv_content_too_long = 0

    # delete and recreate the corpus directory
    shutil.rmtree(str(OUT_DIR), ignore_errors=True)
    OUT_DIR.mkdir()

    # prepend arguments to csv data
    for scenario in scenario_list:
        if not all(len(arg) < 256 for arg in scenario['arguments'].values()):
            nr_rejcts_arg_too_long += 1
            continue
        file_name = f"{scenario['id']:04d}_prepended"
        csv_content_bytes = (DUCKDB_DIR / Path(scenario['data_file'])).read_bytes()
        # exclude larger files, they are less suitable for fuzzing
        if len(csv_content_bytes) > 5000:
            nr_rejcts_csv_content_too_long += 1
            continue
        argument_bytes = encode_csv_arguments(scenario['arguments'])
        (OUT_DIR / file_name).write_bytes(argument_bytes + csv_content_bytes)
        nr_corpus_files_created += 1

    # some logging:
    print(f"{len(scenario_list)} scenarios considered")
    print(f"{nr_rejcts_arg_too_long} rejected because 'arguments too long'")
    print(f"{nr_rejcts_csv_content_too_long} rejected because 'csv content too long'")
    print(f"{nr_corpus_files_created} corpus files created")


def encode_csv_arguments(arguments: dict[str, str]) -> bytes:
    # header: 1 byte with the number of arguments
    assert len(arguments) < 256
    encoded_arguments = len(arguments).to_bytes(1)

    # encoding per argument:
    # 1 byte: param_name (enum)
    # 1 byte: length of argument value (max 255) -> N
    # N bytes: argument value
    for param_name, value in sorted(arguments.items()):
        assert len(value) < 256

        if param_name not in READ_CSV_PARAMETERS_DICT:
            raise ValueError(f'error: unknown argument: {param_name}')
        param_idx = READ_CSV_PARAMETERS_DICT[param_name][0]
        param_type = READ_CSV_PARAMETERS_DICT[param_name][1]
        match param_type:
            case 'BOOLEAN':
                if 'true' in value.lower() or '1' in value:
                    value = '1'
                elif 'false' in value.lower() or '0' in value:
                    value = '0'
                else:
                    raise ValueError(f"invalid boolean value: {value}")
                encoded_arguments = encoded_arguments + (param_idx.to_bytes(1) + (1).to_bytes(1) + value.encode())
            case 'INTEGER':
                try:
                    value = int(value)
                except ValueError:
                    print(f"value '{value}' not usable for param '{param_name}'; default value '42' used instead.")
                    value = 42
                encoded_arguments = encoded_arguments + (
                    param_idx.to_bytes(1) + (8).to_bytes(1) + int(value).to_bytes(length=8, byteorder='little', signed=True)
                )
            case 'VARCHAR':
                encoded_arguments = encoded_arguments + (
                    param_idx.to_bytes(1) + len(value.encode()).to_bytes(1) + value.encode()
                )
            case _:
                raise ValueError(f"invalid parameter type: {param_type}")
    return encoded_arguments


if __name__ == "__main__":
    main()
