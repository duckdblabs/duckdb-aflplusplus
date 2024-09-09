# duckdb_aflplusplus
Fuzzing DuckDB with AFL++

Implemented fuzz tests:
- fuzz test the csv reader: function `read_csv()`
- fuzz test the json reader: function `read_json()`
- fuzz test the json reader: function `read_parquet()`

## AFL++
AFL++ is a fuzzer that comes with its own compiler.

Fuzzing with AFL++ is a multi-step process
(also see [fuzzing_in_depth](https://github.com/AFLplusplus/AFLplusplus/blob/stable/docs/fuzzing_in_depth.md#a-selecting-the-best-afl-compiler-for-instrumenting-the-target)):
1. Create a **target executable** by compiling duckdb with the `afl-clang-fast++` compiler
2. Provide an **input corpus** with typical inputs. E.g. all kinds of valid and invalid csv, json and parquet data.
3. **Fuzzing itself**. `afl++` will call the executable with various inputs based on the corpus to see if it can make it crash
4. **Evaluate the fuzz outputs.** Many inputs will be invalid, and are supposed to give a gracefull error. Inputs that result in a crash, however indicate that there is a bug. These crash cases need to be evaluated to see if they are reproducible outside the fuzzer.

## Locally run AFL++ for DuckDB
Fuzz duckdb with afl++ by executing the folowing steps consequtively.

0. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
1. Create [afl++ container](https://hub.docker.com/r/aflplusplus/aflplusplus) and clone the latest version of duckdb in it. Compiling duckdb and running the fuzzer happens in this container.
    - `make afl-up`
2. Compile executables that can be fuzz-tested
    - `make compile-csv`
    - `make compile-json`
    - `make compile-parquet`
3. Run fuzz tests
    - `make fuzz-csv-reader`
    - `make fuzz-json-reader`
    - `make fuzz-parquet-reader`
4. Inspect the fuzz results to see if there are any inputs that resulted in crashes. They are stored in:
    - `fuzztests/fuzz_results_csv_reader/default/crashes`
    - `fuzztests/fuzz_results_json_reader/default/crashes`
    - `fuzztests/fuzz_results_parquet_reader/default/crashes`
5. Clean up. The container keeps spinning unless explictly stopped; don't skip this step, check with `docker ps`.
    - `make afl-down`

## Fuzz settings
The fuzzing settings are currently hardcoded in the `Makefile` in targets `fuzz-csv-reader`, `fuzz-json-reader` and `fuzz-parquet-reader`. To see all options:
- `make man-page` (when the container is running)
