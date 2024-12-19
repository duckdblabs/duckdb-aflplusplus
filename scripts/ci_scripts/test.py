#!/usr/bin/env python3

import subprocess
import os
import glob

try:
    subprocess.run(["make", "compile-fuzzers-CI"], check=True)
    print(f"Fuzzers are compiled successfully.")
except subprocess.CalledProcessError as e:
    print(f"Make compile command failed with error: {e}")


file_types = ["csv", "json", "parquet", "duckdb", "wal"]
# fuzzing_type = ["file", "pipe", "file-parameter"]
for file_type in file_types:
    fuzz_command = [
        "make",
        f"fuzz-{ file_type }-file"
        ]
    try:
        subprocess.run(fuzz_command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Make fuzz command failed with error: {e}")

    print(f"➡️ Run Tests")

    crashes_dir = "fuzz_results/*_file_fuzzer/default/crashes/"
    files = glob.glob(crashes_dir)
    if len(files) > 0:
        switch file_type:
            case "csv" | "parquet":
                reproduce_command = [
                    "bash",
                    f"scripts/test_{ file_type }_reader.sh"
                    ]
            case "duckdb":
                reproduce_command = [
                    "bash",
                    "scripts/test_duckdb_output.sh"
                ]
            case  "wal": # wal does everything for all crash files
                fix_command = [
                    "bash",
                    "./scripts/fix_wal_files.sh"
                ]
                reproduce_command = [
                    "bash",
                    "./scripts/wal_replay.sh"
                ]
                try:
                    subprocess.run(fix_command, check=True, text=True, capture_output=True)
                except subprocess.CalledProcessError as e:
                    print(f"Script run failed with error: {e}")
            case _:
                pass  # TODO: Hadle json and all other types later
        try:
            subprocess.run(reproduce_command, check=True, text=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"Make fuzz { file_type } failed with error: {e}")
    else:
        print(f"Crashes directories are empty.")    