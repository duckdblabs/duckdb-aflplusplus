## fuzztest_csv
Compiling via the Makefile yields an executable that reads csv from standard-in and calls the duckdb csv importer with it.
When compiled the afl-clang-fast++ compiler, it can be used in afl++ fuzz tests.

### compiling for local use (outside of container with AFL++)
`make CXX=clang++ CC=clang DUCKDB_DIR="/my_path/duckdb"`
