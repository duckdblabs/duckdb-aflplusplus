# duckdb_aflplusplus
Fuzzing DuckDB with AFL++

Implemented fuzz tests:
- fuzz test the csv reader: function `read_csv()`
- fuzz test the json reader: function `read_json()`
- fuzz test the parquet reader: function `read_parquet()`
- fuzz test attaching duckdb storage files
- fuzz test processing write-ahead log file (wal)

## The fuzz process
AFL++ is a fuzzer that comes with its own compiler.

Fuzzing DuckDB with AFL++ is a multi-step process
(also see [fuzzing_in_depth](https://github.com/AFLplusplus/AFLplusplus/blob/stable/docs/fuzzing_in_depth.md#a-selecting-the-best-afl-compiler-for-instrumenting-the-target)). Note that there are make-commands to run most of these steps, they are listed further down.
1. Create a **target executable** by compiling the duckdb library and the wrapper source code with the main function with the `afl-clang-fast++` compiler.
2. Provide an **input corpus** with typical inputs (valid or invalid). Depending on the fuzz scenario, this can be:
    - data inputs files: csv, json, parquet
    - duckdb database files - created by script `create_duckdb_file_corpus.sh`
    - duckdb wal files (write-ahead log) - created by script `create_wal_file_corpus.sh`
3. **Fuzzing itself**

    `afl++` will call the target executable with various inputs based on the corpus to see if it can make it crash. The steps are as follows:
    - AFL++ fuzzer
        - creates (binary) test-data based on the corpus
        - repeatedly calls the target executable, each run providing different test-data as input (stdin)
    - Target executable
        - reads the test-data from stdin
        - stores the data in a temporary file or pipe
        - if applicable, post-processes the incoming data to fix checksums, magic bytes, and size information, to prevent simple rejection scenarios
        - in some cases (e.g. `fuzz-csv-file-parameter`) the post-processing also determines which extra parameters apply when calling specific duckdb functions
        - calls duckdb library function to process the data
    - DuckDB library functions
        - try to ingest and process the test-data; in case of bugs, this might crash the target executable
    - AFL++ fuzzer
        - keeps track of crashing scenarios and store them as fuzz results

4. **Inspect fuzz results**

    - The fuzz results need to be inspected to see if there are any inputs that resulted in crashes.
    - The fuzz results are copied from the container to this repository to new directory `fuzz_results`.
    - Note that many generated inputs will be invalid, but will give a graceful error. These cases are OK, so they will not go into the `crashes` subfolder.

4. **Reproduce crashes**

    Note: the `fuzz_results` directory contains the original inputs, before they were post-processed!
    - For csv, json, and parquet inputs, the crash cases should directly reproducible by importing these files into duckdb:
        - `$ duckdb -c "SELECT * FROM read_csv('my_csv_file')"`
        - `$ cat my_csv_file | duckdb -c "SELECT * FROM read_csv('/dev/stdin')"`
        - `$ duckdb -c "SELECT * FROM read_json('my_json_file')"`
        - `$ cat my_json_file | duckdb -c "SELECT * FROM read_json('/dev/stdin')"`
        - `$ duckdb -c "SELECT * FROM read_parquet('my_parquet_file')"`
    - When fuzzing the csv reader with extra parameters (`fuzz-csv-file-parameter`), the crashes should be reproduced with script: `reproduce_csv_parameter_fuzzer_crashes.py`. The reason is that the first byte contains the parameter scenario info, and is not part of the actual csv input.
    - For duckdb file inputs, the input files from AFL++ should be post-processed with script `fix_duckdb_file.py`. Afterwards, they can be reproduced by opening the duckdb file with duckdb:
        - `$ duckdb my_duckdb_file`
        - `$ duckdb -c "ATTACH 'my_duckdb_file' AS tmp_db (READ_ONLY); use tmp_db; show tables;"`

        To reproduce the entire output folder `fuzz_results/duckdb_file_fuzzer/default/crashes`, use script `test_duckdb_output.sh`.
    - For wal inputs, the AFL++ input files should be post-processed with script `fix_wal_file.py` or in bulk with `fix_wal_files.sh`. A corresponding database file is required to process the fixed wal file. Note that the database file is constant (`base_db`), while the wal file is different each run of the fuzzer.
    To reproduce a crash, rename the crashing wal file to `base_db.wal`, place it next to `base_db` and open `base_db` with duckdb.
        To create the `base_db`:
        ```bash
        source ./scripts/create_base_db.sh
        create_base_db
        ```
        To reproduce the entire output folder `fuzz_results/wal_fuzzer/default/crashes`, first run `fix_wal_files.sh`, followed by `wal_replay.sh`

## Run the AFL++ fuzzer for DuckDB in local container
Fuzz duckdb with afl++ by executing the folowing steps consequtively.

0. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
1. Create an [afl++ container](https://hub.docker.com/r/aflplusplus/aflplusplus) and clone the latest version of duckdb in it. Compiling duckdb and running the fuzzer happens in this container.
    - `make afl-up`
2. Compile executables that can be fuzz-tested
    - `make compile-fuzzers`
3. Run one or more fuzz tests (see the `Makefile` for the corpus selection and fuzz options)
    - `make fuzz-csv-file`
    - `make fuzz-csv-file-parameter`
    - `make fuzz-csv-pipe`
    - `make fuzz-json-file`
    - `make fuzz-json-pipe`
    - `make fuzz-parquet-file`
    - `make fuzz-duckdb-file`
    - `make fuzz-wal-file`
4. Inspect the fuzz results. See above.
5. Clean up. The container keeps spinning unless explictly stopped; don't skip this step, check with `docker ps`.
    - `make afl-down`

## Fuzz settings
The fuzzing settings are currently hardcoded in the `Makefile` in targets `fuzz-csv-file`, `fuzz-csv-pipe`, `fuzz-json-file`, `fuzz-json-pipe`, `fuzz-parquet-file`, `fuzz-duckdb-file`, and `fuzz-wal-file`. To see all options:
- `make man-page` (when the container is running)

## Locally compiling the fuzz-executables, without AFL++
Normally, fuzz executables are compiled inside the AFL++ container, with the `afl-clang-fast++` compiler.
Locally building the fuzz-executables can be useful for develop/debug purposes. Crash-cases found by the fuzzer should be reproducible by the duckdb-cli, but if they are not there is also the option to debug with locally built fuzz-executables.

Steps:

1. Compile DuckDB source code

    Checkout the duckdb source code (`duckdb/duckdb`) and compile
    ```bash
    cd /my_path/duckdb
    make GEN=ninja BUILD_JSON=1 CRASH_ON_ASSERT=1
    ```
2. Compile fuzz-executables

    Compile fuzz-executables with normal `clang++` compiler instead of `afl-clang-fast++`:
    ```bash
    make DUCKDB_LOCAL_DIR=/my_path/duckdb compile-fuzzers-local
    ```
    alternatively, change the DUCKDB_LOCAL_DIR variable in the Makefile, so you can just use `make compile-fuzzers-local`

3. Run fuzz-executables;
    - **csv, json, parquet file readers**:
        feed the content of a file to the executalbe
        ```bash
        < test.csv ./build/csv_file_fuzzer
        ```
        alternatively, you can manually type the input and end with `EOF` (`CTRL-D`);
        ```bash
        ./build/csv_file_fuzzer
        ```
    - **duckdb_file_fuzzer / fuzz-csv-file-parameter**:
        Similar to the file readers above. DuckDB files and csv files with extra parameter info created by the afl++ fuzzer need to be post-processed. See section "reproduce crashes" above.
    - **wal_fuzzer**:
        wal files created by the afl++ fuzzer need to be post-processed. See section "reproduces crashes" above.
        To process wal files, the base_db should also be present.
        ```bash
        # create base_db in build dir
        source ./scripts/create_base_db.sh
        cd build
        create_base_db
        cd ..

        # create valid wal files
        ./scripts/create_wal_file_corpus.sh

        # run wal_fuzzer
        < ./corpus/walfiles/create1.wal ./build/wal_fuzzer
        ```
