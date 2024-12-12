#!/usr/bin/env python3

'''
Script to convert csv files with prepended parameter info into a csv file and a parameter string.
Use it to convert results from into reproducible scenarios:
- use the csv file and parameter string with read_csv()
The decoding logic should be kept in sync with:
- csv_parameter_flex_fuzzer.cpp  (same decoding logic, but with c++, used during fuzzing)
- create_prepended_csv_corpus.py  (encodes and prepends parameter string to csv file)
'''

from pathlib import Path
import json

# NOTE: keep this list in sync with:
#  - 'create_prepended_csv_corpus.py' AND
#  - 'csv_parameter_flex_fuzzer.cpp'
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


# duckdb should be compiled with: BUILD_JSON=1 CRASH_ON_ASSERT=1
DUCKDB_PATH = Path("~/git/duckdb/build/release/duckdb").expanduser()
FUZZ_RESULT_PATH = Path("~/Desktop/crashes").expanduser()
REPRODUCTION_PATH = Path("~/Desktop/csv_issues").expanduser()

def main():
    reproductions = []
    REPRODUCTION_PATH.mkdir(parents=True, exist_ok=True)

    for count, fuzz_file in enumerate(sorted(FUZZ_RESULT_PATH.iterdir())):
        if "README.txt" == fuzz_file.name:
            # skip readme file that afl++ adds to the 'crashes' directory
            continue
        argument_str, file_content = decode_file(fuzz_file)
        file_name = f"case_{count}"
        (REPRODUCTION_PATH / file_name).write_bytes(file_content)
        reproductions.append({'file_name': file_name, 'arguments': argument_str})

    with (REPRODUCTION_PATH / "_REPRODUCTIONS.json").open('w') as reproduction_file:
        json.dump(reproductions, reproduction_file, indent=4)


def decode_file(fuzz_file: Path) -> tuple[str, str]:
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
        param_enum = content[idx] % len(READ_CSV_PARAMETERS)
        idx += 1
        param_name = READ_CSV_PARAMETERS[param_enum][0]
        param_type = READ_CSV_PARAMETERS[param_enum][1]
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
            case 'VARCHAR':
                argument_content = content[idx : idx + argument_length].decode(errors='ignore')
            case _:
                raise ValueError(f"invalid parameter type: {param_type}")
        idx += argument_length
        arg_str = param_name + "=" + argument_content
        arg_str_total = arg_str_total + ", " + arg_str if arg_str_total else arg_str

    file_content = content[idx:]
    return (arg_str_total, file_content)


if __name__ == "__main__":
    main()
