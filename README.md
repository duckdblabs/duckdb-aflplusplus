# duckdb_aflplusplus
Fuzzing DuckDB with AFL++

## fuzzing function read_csv()
Run the following commands consequtively to fuzz-test the read_csv function:
- `make afl-up`
- `make afl-compile`
- `make afl-run`

Clean up afterwards with
- `make afl-clean`

## inspect fuzz results
You can find the crashing scenarios found by the fuzzer, if any, in directory: `fuzz_results/default/crashes`.

## fuzzing settings
The fuzzing settings are currently hardcoded in the Makefile in target `afl-run`.
