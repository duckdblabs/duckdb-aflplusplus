from io import TextIOWrapper
from pathlib import Path

# input
# note: use a duckdb debug build, so assertions are also tested
DUCKDB_REPO = Path("~/git/duckdb").expanduser()
PARQUET_FILES = DUCKDB_REPO / 'data/parquet-testing/fuzzer/20240923_parquet_files_fuzz_error'

# output
SQLLOGIC_TEST = DUCKDB_REPO / f'test/fuzzer/afl/parquet/{PARQUET_FILES.name}.test'


def main():
    parquet_files = sorted(PARQUET_FILES.iterdir())
    if not parquet_files:
        exit(f'Error: no files in dir {PARQUET_FILES}')
    with SQLLOGIC_TEST.open('w') as test_file:
        add_test_header(test_file)
        add_count_test(test_file, len(parquet_files))
        for parquet_file in parquet_files:
            add_test(test_file, parquet_file)


def add_test_header(test_file: TextIOWrapper):
    header = f"""# name: {SQLLOGIC_TEST.name}
# description: test fuzzer generated parquet files - should not raise internal exception (by failed assertion).
# group: [parquet]

require parquet

statement ok
PRAGMA enable_verification

"""
    test_file.write(header)


def add_count_test(test_file: TextIOWrapper, count: int):
    count_test = f"""query I
select count(file) from glob('./{PARQUET_FILES.relative_to(DUCKDB_REPO)}/*');
----
{count}

"""
    test_file.write(count_test)


def add_test(test_file: TextIOWrapper, parquet_file: Path):
    test = f"""statement maybe
FROM read_parquet('{parquet_file.relative_to(DUCKDB_REPO)}');
----

"""
    test_file.write(test)


if __name__ == "__main__":
    main()
