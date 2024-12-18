#!/usr/bin/env python3

import subprocess

try:
    subprocess.run(["make", "compile-fuzzers-CI"], check=True)
    print(f"Fuzzers are compiled successfully.")
except subprocess.CalledProcessError as e:
    print(f"Make compile command failed with error: {e}")


file_types = ["csv", "json", "parquet", "duckdb", "wal"]
for file_type in file_types:
    try:
        subprocess.run(["make", f"fuzz-{ file_type }-file"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Make fuzz command failed with error: {e}")

