# duckdb-aflplusplus
Fuzzing DuckDB with AFL++

Implemented fuzz tests:
- fuzz test the csv reader: function `read_csv()`
- fuzz test the json reader: function `read_json()`
- fuzz test the parquet reader: function `read_parquet()`
- fuzz test attaching duckdb storage files
- fuzz test processing write-ahead log file (wal)

## The fuzz process
AFL++ is a fuzzer that comes with its own compiler.
(Also see [fuzzing_in_depth](https://github.com/AFLplusplus/AFLplusplus/blob/stable/docs/fuzzing_in_depth.md#a-selecting-the-best-afl-compiler-for-instrumenting-the-target)).

Fuzzing DuckDB with AFL++ consists of the following steps.
Note that there are make-commands to run most of these steps, they are listed further down.

1. Create a **target executable** by compiling the duckdb library and the wrapper source code with the main function with the `afl-clang-fast++` compiler.

2. Provide an **input corpus** with typical inputs (valid or invalid). Depending on the fuzz scenario, this can be:
    - data inputs files: csv, json, parquet - taken from `duckdb/data`
    - duckdb database files - created by script `create_duckdb_file_corpus.sh`
    - duckdb wal files (write-ahead log) - created by script `create_wal_file_corpus.sh`

    Note: for the 'multi-param' fuzzers, the input corpus needs to be pre-processed. See: [Appendix A - encoding arguments to corpus files](#appendix-a---encoding-arguments-to-corpus-files)

3. **Fuzzing itself**

    `afl++` will call the target executable with various inputs based on the corpus to see if it can make it crash. The steps are as follows:
    - AFL++ fuzzer
        - creates (binary) test-data based on the corpus, introducing semi random mutations
        - repeatedly calls the target executable, each run providing different test-data as input (stdin)
    - Target executable
        - reads the test-data from stdin
        - if applicable, pre-processes the incoming data, depending on the fuzz target this may include:
            - fix checksums, magic bytes, and size information, to prevent simple rejection scenarios
            - [decode](#appendix-a---encoding-arguments-to-corpus-files) prepended argument information. The argument information is not part of the file that needs to be ingested by duckdb.
        - stores the data that needs to be ingested in a temporary file or pipe
        - calls duckdb library function (with the decoded arguments) to process the data
    - DuckDB library functions
        - tries to ingest and process the test-data; in case of bugs, this might crash the target executable
    - AFL++ fuzzer
        - keeps track of crashing scenarios and store them as fuzz results

4. **Inspect fuzz results**
    - The fuzz results need to be inspected to see if there are any inputs that resulted in 'crashes' or 'hangs'.
    - The fuzz results are copied from the container to this repository to new directory `fuzz_results`.
    - Note that many generated inputs will be invalid, but will give a graceful error. These cases are OK, so they will not go into the `crashes` or `hangs` subdirectories. Scenarios with bugs will be in the `crashes` or `hangs` subdirectories.

5. **Reproduce crashes**

    Note: the `fuzz_results` directory contains the original inputs, before they were processed by the target executable!

    The reproduction depends on the fuzzer:
    - For csv, json, and parquet inputs without any additional arguments (`base_fuzzer` and `pipe_fuzzer`), the crash cases should be directly reproducible by importing these files into duckdb:
        - `$ duckdb -c "SELECT * FROM read_csv('my_csv_file')"`
        - `$ cat my_csv_file | duckdb -c "SELECT * FROM read_csv('/dev/stdin')"`
        - `$ duckdb -c "SELECT * FROM read_json('my_json_file')"`
        - `$ cat my_json_file | duckdb -c "SELECT * FROM read_json('/dev/stdin')"`
        - `$ duckdb -c "SELECT * FROM read_parquet('my_parquet_file')"`
    - For `csv_single_param_fuzzer`, the crashes should be reproduced with script: `test_csv_reader_single_param.py`. The reason is that the first byte contains the parameter scenario info, and is not part of the actual csv input.
    - For `multi_param_fuzzer`, the crashes cases should first be decoded with script `decode_fuzz_result.py`. See step 5 of [Appendix A - encoding arguments to corpus files](#appendix-a---encoding-arguments-to-corpus-files).
    - For duckdb file inputs (`duckdb_file_fuzzer`), the input files from AFL++ should be post-processed with script `fix_duckdb_file.py`. Afterwards, they can be reproduced by opening the duckdb file with duckdb:
        - `$ duckdb my_duckdb_file`
        - `$ duckdb -c "ATTACH 'my_duckdb_file' AS tmp_db (READ_ONLY); use tmp_db; show tables;"`

        To reproduce the entire output folder `fuzz_results/duckdb_file_fuzzer/default/crashes`, use script `test_duckdb_output.sh`.
    - For wal inputs (`wal_fuzzer`), the AFL++ input files should be post-processed with script `fix_wal_file.py` or in bulk with `fix_wal_files.sh`. A corresponding database file is required to process the fixed wal file. Note that the database file is constant (`base_db`), while the wal file is different each run of the fuzzer.
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
    - `make fuzz-csv-base`
    - `make fuzz-csv-single-param`
    - `make fuzz-csv-multi-param`
    - `make fuzz-csv-pipe`
    - `make fuzz-json-base`
    - `make fuzz-json-multi-param`
    - `make fuzz-json-pipe`
    - `make fuzz-parquet-base`
    - `make fuzz-duckdb-file`
    - `make fuzz-wal-file`

    Note: these make targets als create or select the required corpus.
4. Inspect the fuzz result. See above.
5. If there are 'crashes' or 'hangs', create reproducible cases to file the issue. See above
6. Clean up. The container keeps spinning unless explictly stopped; don't skip this step, check with `docker ps`.
    - `make afl-down`

## Fuzz settings
The fuzzing settings are currently hardcoded in the `fuzz-*` targets in the `Makefile`. To see all options:
- `make man-page` (when the container is running)

## Locally compiling the fuzz-executables, without AFL++
Normally, fuzz executables are compiled inside the AFL++ container, with the `afl-clang-fast++` compiler.
Locally building the fuzz-executables can be useful for develop/debug purposes. Crash-cases found by the fuzzer should be reproducible by the duckdb-cli, but if they are not there is also the option to debug with locally built fuzz-executables.

Steps:

1. Compile DuckDB source code

    Checkout the duckdb source code (`duckdb/duckdb`) and compile with the following flags:
    ```bash
    cd /my_path/duckdb
    make GEN=ninja BUILD_JSON=1 BUILD_JEMALLOC=1 CRASH_ON_ASSERT=1
    ```
2. Compile fuzz-executables

    Compile fuzz-executables with normal `clang++` compiler instead of `afl-clang-fast++`:
    ```bash
    make DUCKDB_LOCAL_DIR=/my_path/duckdb compile-fuzzers-local
    ```
    alternatively, change the DUCKDB_LOCAL_DIR variable in the Makefile, so you can just use `make compile-fuzzers-local`

3. Run fuzz-executables;
    feed the content of a file to the executalbe, for example:
    ```bash
    < test.csv ./build/csv_base_fuzzer
    ```
    Notes:
    - for `base_fuzzer` and `pipe_fuzzer` (ingesting csv/json/parquet data): no special considerations

    - for `csv_single_param_fuzzer`: note that the the first byte is used to determine the parameter for read_csv() and is not considered part of the data file.

    - for `multi_param_fuzzer`, the executable assumes the input contains prepended argument info. Data from the `fuzz_results` can directly fed to the executable, since it is based on a corpus that also contains prepended argument info. Files created by `create_multi_param_corpus.py` can also be directly used.

    - for `duckdb_file_fuzzer`, any duckdb file (created by afl++ or not) can directly be fed to the executable.

        Note that `duckdb_file_fuzzer` also executes a fixup script.

    - for `wal_fuzzer`, any wal file (created by afl++ or not) can directly be fed to the executable, however, a `base_db` file also needs to be present.

        Note that `wal_fuzzer` also executes a fixup script.

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

## Appendix A - encoding arguments to corpus files

To effectively fuzz the file readers, we not only want to test with a variety of csv/json/parquet files, but also want to run with different arguments like `ignore_errors=true`, `skip=42`, etc.

The AFL++ fuzzer, however, doesn't natively supports this multi-dimensionality, since it produces a single byte stream input for the fuzz target.

A way to circumvent this is by asumming that the first part of the byte input is encoded argument information, rather then the csv/json/parquet content itself.

By prepending the corpus files with encoded argument information, the fuzzer will create similar inputs for the fuzz executable.

Steps:

0. Run a make command (it will do the other steps, except step 5):
    - `make fuzz-csv-multi-param`
    - `make fuzz-json-multi-param`

1. Create a json file that lists the base corpus data together with the arguments.
    - script: `create_multi_param_corpus_info.py`
    - example:
    ```json
    [
        {
            "id": 1,
            "data_file": "data/csv/rejects/multiple_errors/invalid_utf_more.csv",
            "arguments": {
                "store_rejects": "true",
                "header": "1",
                "max_line_size": "40",
                "auto_detect": "false",
                "columns": "{'name': 'VARCHAR', 'age': 'INTEGER', 'current_day': 'DATE', 'barks': 'INTEGER'}"
            }
        },
        {
            "id": 2,
            "data_file": "data/csv/auto/int_bol.csv",
            "arguments": {
                "dtypes": "['varchar', 'varchar', 'varchar']"
            }
        }
    ]
    ```

2. Encode and prepend the additional arguments to the data files to create the corpus.
    - script: `create_multi_param_corpus.py`
    - See [this article](https://securitylab.github.com/resources/fuzzing-challenges-solutions-1/#fuzzing-command-line-arguments) for the main idea.
    - The following encoding is used:
        - single header byte: 1 byte (unsigned char) with the number of arguments
        - followed by encoding per argument:
            - 1 byte: param_name (enum)
            - 1 byte: length of argument value (max 255) -> N
            - N bytes: argument value
        - N values per data type:
            - BOOLEAN: N=1 (odd values decode to true, even values to false)
            - INTEGER: N=8 (8 byte singed integer)
            - DOUBLE: N=8 (8 byte double precision float)
            - VARCHAR: N=[0-255] depending on length of argument value

3. The fuzzer generates inputs based on the prepended corpus files.
Therefore it might mutate both the leading bytes with the argument info and/or the remainder with the actual input file.
Since the parameter names are stored with an enum, the parameters used in the function call might change, as well as their values.
The fuzzer might also change the N values, in case the N value is incompatible with argument data type, fallback values are used.

4. The target executable decodes the prepended argument bytes and trims them from the input data. The duckdb function is called with the decoded argument string.

5. To reproduce crashses found this way use `decode_fuzz_result.py` to recreate the argument string / input file combinations that caused crashes. Afterwards, the reproducible scenarios created this way can be executed by scripts like:
    - `test_csv_reader_with_args.py`
    - `test_json_reader_with_args.py`
