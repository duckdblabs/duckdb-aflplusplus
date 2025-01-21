#!/usr/bin/env python3

'''
This script reverses the encoding done by script 'create_multi_param_corpus.py'
Input:
  - a directory of csv, json or parquet files with prepended argument info
Output:
  - a directory with regular csv, json or parquet files
  - a json file with the associated argument string per csv/json/parquet file
Usage:
  - The script can be used to convert fuzz results into reproducible scenarios.
  - Reproduce the fuzz result by igesting the original file with read_csv() / read_json() / read_parquet() with the argument string.
Note:
  - The decoding logic should be kept in sync with:
    - file_fuzzer_multi_param.cpp (same decoding logic, but with c++, used during fuzzing)
    - create_multi_param_corpus.py (encodes and prepends parameter string to a csv/json/parquet file)
'''

from pathlib import Path
import json
import re
import struct
import sys

# duckdb should be compiled with: BUILD_JSON=1 CRASH_ON_ASSERT=1
DUCKDB_PATH = Path("~/git/duckdb/build/release/duckdb").expanduser()
FUZZ_SRC_DIR = Path(__file__).parents[2] / 'src'
INPUT_DIR = Path("~/Desktop/crashes").expanduser()
OUTPUT_DIR = Path("~/Desktop/reproductions").expanduser()


def main(argv: list[str]):
    target_function = argv[1]
    match target_function:
        case 'read_csv':
            parameters = read_tuples_from_cpp(FUZZ_SRC_DIR / 'csv_parameters.cpp')
            extension = '.csv'
        case 'read_json':
            parameters = read_tuples_from_cpp(FUZZ_SRC_DIR / 'json_parameters.cpp')
            extension = '.json'
        case 'read_parquet':
            parameters = read_tuples_from_cpp(FUZZ_SRC_DIR / 'parquet_parameters.cpp')
            extension = '.parquet'
        case _:
            raise ValueError(f"invalid input: {target_function}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    reproductions = []
    for count, fuzz_file in enumerate(sorted(INPUT_DIR.iterdir())):
        if fuzz_file.name == "README.txt":
            # skip readme file that afl++ adds to the 'crashes' directory
            continue
        argument_str, file_content = decode_file(fuzz_file, parameters)
        file_name = f"case_{count}{extension}"
        (OUTPUT_DIR / file_name).write_bytes(file_content)
        reproductions.append({'file_name': file_name, 'arguments': argument_str})

    with (OUTPUT_DIR / "_REPRODUCTIONS.json").open('w') as reproduction_file:
        json.dump(reproductions, reproduction_file, indent=4)


def decode_file(fuzz_file: Path, parameters: list[tuple[str, str]]) -> tuple[str, str]:
    content = fuzz_file.read_bytes()
    nr_bytes = len(content)
    arg_str_total = ""

    # decode header: 1 byte (unsigned char) with the number of arguments
    idx = 0
    nr_arguments = content[idx]
    idx += 1

    # encoding per argument:
    # 1 byte: param_name (enum)
    # 1 byte: length of argument value (max 255) -> N
    # N bytes: argument value
    for _ in range(nr_arguments):
        if idx + 2 >= nr_bytes:
            break
        param_enum = content[idx] % len(parameters)
        idx += 1
        param_name = parameters[param_enum][0]
        param_type = parameters[param_enum][1]
        argument_length = content[idx]
        idx += 1
        match param_type:
            case 'BOOLEAN':
                if idx < nr_bytes:
                    argument_content = 'true' if (content[idx] % 2) else 'false'
                else:
                    argument_content = 'true'
            case 'INTEGER':
                argument_content = (
                    str(int.from_bytes(content[idx : idx + 8], byteorder='little', signed=True))
                    if argument_length >= 8 and idx + argument_length <= nr_bytes
                    else "42"
                )
            case 'DOUBLE':
                argument_content = (
                    str(struct.unpack("d", content[idx : idx + struct.calcsize('d')])[0])
                    if argument_length >= struct.calcsize('d') and idx + argument_length <= nr_bytes
                    else "0.1"
                )
            case 'VARCHAR':
                argument_content = content[idx : idx + argument_length].decode(errors='ignore')
            case _:
                raise ValueError(f"invalid parameter type: {param_type}")
        idx += argument_length
        arg_str = param_name + "=" + argument_content
        arg_str_total = arg_str_total + ", " + arg_str if arg_str_total else arg_str

    file_content = content[idx:]
    return (arg_str_total, file_content)


# tuples: (parameter_name, parameter_type)
def read_tuples_from_cpp(cpp_source_file: Path) -> list[tuple[str, str]]:
    tuples: list[tuple] = []
    file_content = cpp_source_file.read_text()
    tuple_string: str
    for tuple_string in re.findall(r"std::make_tuple\((.*?)\)", file_content, flags=re.NOFLAG):
        parts = tuple_string.partition(',')
        tuples.append((parts[0].strip('\" '), parts[2].strip('\" ')))
    return tuples


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("ERROR. provide the target function ('read_csv', 'read_json' or 'read_parquet') as first argument")
    main(sys.argv)
