#!/usr/bin/env python3

'''
This script creates a csv fuzz corpus by prepending the parameter info to the csv data.
The input 'CSV_CORPUS_JSON' is created by script 'create_csv_argument_file_corpus.py'
'''

import json
import shutil
from pathlib import Path

CSV_CORPUS_ROOT_DIR = Path(__file__).parents[1] / 'corpus/csv/'
CSV_CORPUS_JSON = CSV_CORPUS_ROOT_DIR / 'csv_parameter.json'
OUT_DIR = CSV_CORPUS_ROOT_DIR / 'corpus_prepended'
DUCKDB_DIR = FILE_DIR_TO_SCRAPE = Path('~/git/duckdb/').expanduser()

# note: types here are simplified to 'BOOLEAN', 'INTEGER', and 'VARCHAR'
# VARCHAR is also used for all complex types (lists, structs, etc)
READ_CSV_PARAMETERS = [
    {"name": "all_varchar", "type": "BOOLEAN"},
    {"name": "allow_quoted_nulls", "type": "BOOLEAN"},
    {"name": "auto_detect", "type": "BOOLEAN"},
    {"name": "auto_type_candidates", "type": "VARCHAR"},
    {"name": "columns", "type": "VARCHAR"},
    {"name": "compression", "type": "VARCHAR"},
    {"name": "dateformat", "type": "VARCHAR"},
    {"name": "decimal_separator", "type": "VARCHAR"},
    {"name": "delim", "type": "VARCHAR"},
    {"name": "delimiter", "type": "VARCHAR"},
    {"name": "dtypes", "type": "VARCHAR"},
    {"name": "escape", "type": "VARCHAR"},
    {"name": "filename", "type": "BOOLEAN"},
    {"name": "force_not_null", "type": "VARCHAR"},
    {"name": "header", "type": "BOOLEAN"},
    {"name": "hive_partitioning", "type": "BOOLEAN"},
    {"name": "ignore_errors", "type": "BOOLEAN"},
    {"name": "max_line_size", "type": "INTEGER"},
    {"name": "names", "type": "VARCHAR"},
    {"name": "new_line", "type": "VARCHAR"},
    {"name": "normalize_names", "type": "BOOLEAN"},
    {"name": "null_padding", "type": "BOOLEAN"},
    {"name": "nullstr", "type": "VARCHAR"},
    {"name": "parallel", "type": "BOOLEAN"},
    {"name": "quote", "type": "VARCHAR"},
    {"name": "sample_size", "type": "INTEGER"},
    {"name": "sep", "type": "VARCHAR"},
    {"name": "skip", "type": "INTEGER"},
    {"name": "timestampformat", "type": "VARCHAR"},
    {"name": "types", "type": "VARCHAR"},
    {"name": "union_by_name", "type": "BOOLEAN"},
    # undocumented
    {"name": "buffer_size", "type": "INTEGER"},
    {"name": "column_names", "type": "VARCHAR"},
    {"name": "column_types", "type": "VARCHAR"},
    {"name": "comment", "type": "VARCHAR"},
    {"name": "date_format", "type": "VARCHAR"},
    {"name": "encoding", "type": "VARCHAR"},
    {"name": "force_quote", "type": "VARCHAR"},
    {"name": "hive_type", "type": "VARCHAR"},
    {"name": "hive_type_autocast", "type": "BOOLEAN"},
    {"name": "hive_types", "type": "VARCHAR"},
    {"name": "hive_types_autocast", "type": "BOOLEAN"},
    {"name": "maximum_line_size", "type": "INTEGER"},
    {"name": "null", "type": "VARCHAR"},
    {"name": "prefix", "type": "VARCHAR"},
    {"name": "rejects_limit", "type": "INTEGER"},
    {"name": "rejects_scan", "type": "VARCHAR"},
    {"name": "rejects_table", "type": "VARCHAR"},
    {"name": "rfc_4180", "type": "BOOLEAN"},
    {"name": "store_rejects", "type": "BOOLEAN"},
    {"name": "suffix", "type": "VARCHAR"},
    {"name": "timestamp_format", "type": "VARCHAR"},
]

PARAMETER_NAMES = [param['name'] for param in READ_CSV_PARAMETERS]


def main():
    file_content = CSV_CORPUS_JSON.read_text()
    scenario_list = json.loads(file_content)
    nr_corpus_files_created = 0
    nr_rejcts_arg_too_long = 0
    nr_rejcts_csv_content_too_long = 0

    # delete and recreate the corpus directory
    shutil.rmtree(str(OUT_DIR), ignore_errors=True)
    OUT_DIR.mkdir()

    # prepend arguments to csv data
    for count, scenario in enumerate(scenario_list):
        if not all(len(arg) < 256 for arg in scenario['arguments'].values()):
            nr_rejcts_arg_too_long += 1
            continue
        file_name = f"{count:04d}_prepended_csv"
        csv_content_bytes = (DUCKDB_DIR / Path(scenario['data_file'])).read_bytes()
        # exclude big files, they are less suitable for fuzzing
        if len(csv_content_bytes) > 500:
            nr_rejcts_csv_content_too_long += 1
            continue
        argument_bytes = encode_csv_arguments(scenario['arguments'], count)
        (OUT_DIR / file_name).write_bytes(argument_bytes + csv_content_bytes)
        nr_corpus_files_created += 1

    # some logging:
    print(f"{len(scenario_list)} scenarios considered")
    print(f"{nr_rejcts_arg_too_long} rejected because 'arguments too long'")
    print(f"{nr_rejcts_csv_content_too_long} rejected because 'csv content too long'")
    print(f"{nr_corpus_files_created} corpus files created")


def encode_csv_arguments(arguments: dict[str, str], scenario_count: int) -> bytes:
    # header: 1 byte with the number of arguments
    assert len(arguments) < 256
    encoded_arguments = len(arguments).to_bytes()

    # encoding per argument:
    # 1 byte: param_name (enum)
    # 1 byte: length of argument value (max 255) -> N
    # N bytes: argument value
    for param_name, value in sorted(arguments.items()):
        assert len(value) < 256
        try:
            param_idx = PARAMETER_NAMES.index(param_name)
        except ValueError:
            raise ValueError(f'error: unknown argument: {param_name}')
        param_type = READ_CSV_PARAMETERS[param_idx]['type']
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
                if not value.isnumeric():
                    print(f"value '{value}' not usable for param '{param_name}'; default value '42' used instead.")
                    value = 42
                encoded_arguments = encoded_arguments + (
                    param_idx.to_bytes(1) + (8).to_bytes(1) + int(value).to_bytes(8)
                )
            case 'VARCHAR':
                encoded_arguments = encoded_arguments + (
                    param_idx.to_bytes(1) + len(value).to_bytes(1) + value.encode()
                )
            case _:
                raise ValueError(f"invalid parameter type: {param_type}")
    return encoded_arguments


if __name__ == "__main__":
    main()
