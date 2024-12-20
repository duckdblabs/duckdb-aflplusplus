#!/usr/bin/env python3

'''
This script creates a fuzz corpus by prepending the parameter info to the data files.
Input:
    - directory 'duckdb/data'
    - file 'csv_parameter.json' or 'json_parameter.json'; created by script 'create_multi_param_corpus_info.py'
    - file 'csv_parameters.cpp' or 'json_parameters.cpp'
Output:
    - a corpus directory to be used with 'multi_param' fuzzers
'''

import json
import re
import shutil
import struct
import sys
from pathlib import Path


DUCKDB_DIR = FILE_DIR_TO_SCRAPE = Path('~/git/duckdb/').expanduser()
CORPUS_ROOT_DIR = Path(__file__).parents[2] / 'corpus'
SRC_DIR = Path(__file__).parents[2] / 'src'


def main(argv: list[str]):
    target_function = argv[1]
    match target_function:
        case 'read_csv':
            parameters = read_tuples_from_cpp(SRC_DIR / 'csv_parameters.cpp')
            corpus_dir = CORPUS_ROOT_DIR / 'csv'
            corpus_json = corpus_dir / 'csv_parameter.json'
            out_dir = corpus_dir / 'corpus_prepended'
        case 'read_json':
            parameters = read_tuples_from_cpp(SRC_DIR / 'json_parameters.cpp')
            corpus_dir = CORPUS_ROOT_DIR / 'json'
            corpus_json = corpus_dir / 'json_parameter.json'
            out_dir = corpus_dir / 'corpus_prepended'
        case _:
            raise ValueError(f"not supported: {target_function}")
    parameter_types = {param[0]: (param_idx, param[1]) for param_idx, param in enumerate(parameters)}

    if not corpus_json.exists():
        print(f"file not found: {corpus_json}")
        exit(1)
    file_content = corpus_json.read_text()
    scenario_list: list[dict] = json.loads(file_content)
    nr_corpus_files_created = 0
    nr_rejects_file_not_found = 0
    nr_rejects_content_too_long = 0
    nr_rejects_arg_too_long = 0

    # delete and recreate the corpus directory
    shutil.rmtree(str(out_dir), ignore_errors=True)
    out_dir.mkdir()

    # prepend arguments to data
    for scenario in scenario_list:
        if not all(len(arg) < 256 for arg in scenario['arguments'].values()):
            nr_rejects_arg_too_long += 1
            continue
        data_file = (DUCKDB_DIR / Path(scenario['data_file']))
        if not data_file.is_file():
            nr_rejects_file_not_found += 1
            continue
        corpus_file_name = f"{scenario['id']:04d}_prepended"
        orig_content_bytes = data_file.read_bytes()
        # exclude larger files, they are less suitable for fuzzing
        if len(orig_content_bytes) > 5000:
            nr_rejects_content_too_long += 1
            continue
        argument_bytes = encode_arguments(scenario['arguments'], parameter_types)
        (out_dir / corpus_file_name).write_bytes(argument_bytes + orig_content_bytes)
        nr_corpus_files_created += 1

    # some logging:
    print(f"{len(scenario_list)} scenarios considered")
    print(f"{nr_rejects_file_not_found} rejected because 'file not found'")
    print(f"{nr_rejects_content_too_long} rejected because 'file content too long'")
    print(f"{nr_rejects_arg_too_long} rejected because 'arguments too long'")
    print(f"{nr_corpus_files_created} corpus files created")


def encode_arguments(arguments: dict[str, str], parameter_types: dict[str, tuple[int, str]]) -> bytes:
    # header: 1 byte with the number of arguments
    assert len(arguments) < 256
    encoded_arguments = len(arguments).to_bytes(1)

    # encoding per argument:
    # 1 byte: param_name (enum)
    # 1 byte: length of argument value (max 255) -> N
    # N bytes: argument value
    for param_name, value in sorted(arguments.items()):
        assert len(value) < 256

        if param_name not in parameter_types:
            raise ValueError(f'error: unknown argument: {param_name}')
        param_idx = parameter_types[param_name][0]
        param_type = parameter_types[param_name][1]
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
                    param_idx.to_bytes(1)
                    + (8).to_bytes(1)
                    + int(value).to_bytes(length=8, byteorder='little', signed=True)
                )
            case 'DOUBLE':
                try:
                    # note: python 'float' is 8 bytes, equal to C++ 'double'
                    value = float(value)
                except ValueError:
                    print(f"value '{value}' not usable for param '{param_name}'; default value '0.1' used instead.")
                    value = 0.1
                encoded_arguments = encoded_arguments + (
                    param_idx.to_bytes(1) + (8).to_bytes(1) + struct.pack("d", value)
                )
            case 'VARCHAR':
                encoded_arguments = encoded_arguments + (
                    param_idx.to_bytes(1) + len(value.encode()).to_bytes(1) + value.encode()
                )
            case _:
                raise ValueError(f"invalid parameter type: {param_type}")
    return encoded_arguments


# tuples: (parameter_name, parameter_type)
def read_tuples_from_cpp(cpp_source_file: Path) -> list[tuple[str, str]]:
    tuples: list[tuple] = []
    file_content = cpp_source_file.read_text()
    tuple_string: str
    for tuple_string in re.findall(r"std::make_tuple\((.*)\)", file_content, flags=re.NOFLAG):
        parts = tuple_string.partition(',')
        tuples.append((parts[0].strip('\" '), parts[2].strip('\" ')))
    return tuples


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("ERROR. provide the target function ('read_csv' or 'read_json') as first argument")
    main(sys.argv)
