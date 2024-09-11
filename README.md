# duckdb_aflplusplus
Fuzzing DuckDB with AFL++

Implemented fuzz tests:
- fuzz test the csv reader: function `read_csv()`
- fuzz test the json reader: function `read_json()`
- fuzz test the parquet reader: function `read_parquet()`

## AFL++
AFL++ is a fuzzer that comes with its own compiler.

Fuzzing with AFL++ is a multi-step process
(also see [fuzzing_in_depth](https://github.com/AFLplusplus/AFLplusplus/blob/stable/docs/fuzzing_in_depth.md#a-selecting-the-best-afl-compiler-for-instrumenting-the-target)):
1. Create a **target executable** by compiling the duckdb library with the `afl-clang-fast++` compiler. The duckdb libaray is included by a main function that specifically executes the functions that need to be tested.
2. Provide an **input corpus** with typical inputs. E.g. all kinds of valid and invalid csv, json and parquet data.
3. **Fuzzing itself**. `afl++` will call the executable with various inputs based on the corpus to see if it can make it crash
4. **Evaluate the fuzz outputs.** Many inputs will be invalid, and are supposed to give a gracefull error. Inputs that result in a crash, however indicate that there is a bug. These crash cases need to be evaluated to see if they are reproducible outside the fuzzer.

## Run AFL++ for DuckDB in local container
Fuzz duckdb with afl++ by executing the folowing steps consequtively.

0. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
1. Create [afl++ container](https://hub.docker.com/r/aflplusplus/aflplusplus) and clone the latest version of duckdb in it. Compiling duckdb and running the fuzzer happens in this container.
    - `make afl-up`
2. Compile executables that can be fuzz-tested
    - `make compile-fuzzers`
3. Run one or more fuzz tests
    - `make fuzz-csv-file`
        -  equivalent: `$ duckdb -c "SELECT * FROM read_csv('my_csv_file')"`
    - `make fuzz-csv-pipe`
        -  equivalent: `$ cat my_csv_file | duckdb -c "SELECT * FROM read_csv('/dev/stdin')"`
    - `make fuzz-json-file`
        -  equivalent: `$ duckdb -c "SELECT * FROM read_json('my_json_file')"`
    - `make fuzz-json-pipe`
        -  equivalent: `$ cat my_json_file | duckdb -c "SELECT * FROM read_json('/dev/stdin')"`
    - `make fuzz-parquet-file`
        -  equivalent: `$ duckdb -c "SELECT * FROM read_parquet('my_parquet_file')"`
4. Inspect the fuzz results to see if there are any inputs that resulted in crashes. Results are copied from the container to new directory `fuzz_results`, for example:
    - `./fuzz_results/csv_file_fuzzer`
5. Clean up. The container keeps spinning unless explictly stopped; don't skip this step, check with `docker ps`.
    - `make afl-down`

## Fuzz settings
The fuzzing settings are currently hardcoded in the `Makefile` in targets `fuzz-csv-file`, `fuzz-csv-pipe`, `fuzz-json-file`, `fuzz-json-pipe`, `fuzz-parquet-file`. To see all options:
- `make man-page` (when the container is running)

## Locally testing the fuzz-executables, without AFL++
- build duckdb with the json extension.
```bash
cd /my_path/duckdb
make GEN=ninja BUILD_JSON=1
```

- create executable (with normal `clang++` compiler instead of `afl-clang-fast++`)
```bash
cd /my_path/duckdb_aflplusplus/fuzztests
make CXX=clang++ CC=clang DUCKDB_DIR=/my_path/duckdb csv_file_fuzzer
```

- run the executalbe:
```bash
./csv_file_fuzzer
```
- manually type csv input and end with `CTRL-D`; alternatively you can pipe the content of a file into the executalbe
