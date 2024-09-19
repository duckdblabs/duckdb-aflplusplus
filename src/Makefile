CSV_FILE_FUZZER=csv_file_fuzzer
CSV_PIPE_FUZZER=csv_pipe_fuzzer
JSON_FILE_FUZZER=json_file_fuzzer
JSON_PIPE_FUZZER=json_pipe_fuzzer
PARQUET_FILE_FUZZER=parquet_file_fuzzer
DUCKDB_FILE_FUZZER=duckdb_file_fuzzer

DUCKDB_DIR=/duckdb
DUCKDBLIB=$(DUCKDB_DIR)/build/release/src/libduckdb_static.a

DUCKDB_DEPS=$(DUCKDB_DIR)/build/release/third_party/fmt/libduckdb_fmt.a \
	$(DUCKDB_DIR)/build/release/third_party/libpg_query/libduckdb_pg_query.a \
	$(DUCKDB_DIR)/build/release/third_party/re2/libduckdb_re2.a \
	$(DUCKDB_DIR)/build/release/third_party/miniz/libduckdb_miniz.a \
	$(DUCKDB_DIR)/build/release/third_party/utf8proc/libduckdb_utf8proc.a \
	$(DUCKDB_DIR)/build/release/third_party/hyperloglog/libduckdb_hyperloglog.a \
	$(DUCKDB_DIR)/build/release/third_party/skiplist/libduckdb_skiplistlib.a \
	$(DUCKDB_DIR)/build/release/third_party/fastpforlib/libduckdb_fastpforlib.a \
	$(DUCKDB_DIR)/build/release/third_party/mbedtls/libduckdb_mbedtls.a \
	$(DUCKDB_DIR)/build/release/third_party/fsst/libduckdb_fsst.a \
	$(DUCKDB_DIR)/build/release/third_party/yyjson/libduckdb_yyjson.a

DUCKDB_EXT=$(DUCKDB_DIR)/build/release/extension/parquet/libparquet_extension.a \
	$(DUCKDB_DIR)/build/release/extension/json/libjson_extension.a

INC=-I$(DUCKDB_DIR)/src/include
CXXFLAGS= -std=c++11
CC=/AFLplusplus/afl-clang-fast
CXX=/AFLplusplus/afl-clang-fast++

all: $(CSV_PIPE_FUZZER) $(JSON_PIPE_FUZZER) $(PARQUET_FUZZER)

# NOTE: after https://github.com/duckdb/duckdb/pull/14033 is merged, use:
# cd $(DUCKDB_DIR) && CC=$(CC) CXX=$(CXX) GEN=ninja BUILD_JSON=1 FORCE_ASSERT=1 CRASH_ON_ASSERT=1 make
$(DUCKDBLIB):
	cd $(DUCKDB_DIR) && CC=$(CC) CXX=$(CXX) GEN=ninja BUILD_JSON=1 CMAKE_VARS_BUILD="-DASSERT_EXCEPTION=0 -DFORCE_ASSERT=1" make

# file reader fuzzers (csv, json, parquet)

$(CSV_FILE_FUZZER): $(DUCKDBLIB) file_reader_fuzzer.cpp
	$(CXX) -D DUCKDB_READ_FUNCTION=\"read_csv\" file_reader_fuzzer.cpp $(INC) $(CXXFLAGS) $(DUCKDBLIB) $(DUCKDB_DEPS) $(DUCKDB_EXT) -o $(CSV_FILE_FUZZER)

$(JSON_FILE_FUZZER): $(DUCKDBLIB) file_reader_fuzzer.cpp
	$(CXX) -D DUCKDB_READ_FUNCTION=\"read_json\" file_reader_fuzzer.cpp $(INC) $(CXXFLAGS) $(DUCKDBLIB) $(DUCKDB_DEPS) $(DUCKDB_EXT) -o $(JSON_FILE_FUZZER)

$(PARQUET_FILE_FUZZER): $(DUCKDBLIB) file_reader_fuzzer.cpp
	$(CXX) -D DUCKDB_READ_FUNCTION=\"read_parquet\" file_reader_fuzzer.cpp $(INC) $(CXXFLAGS) $(DUCKDBLIB) $(DUCKDB_DEPS) $(DUCKDB_EXT) -o $(PARQUET_FILE_FUZZER)


# pipe fuzzers (csv, json)

$(CSV_PIPE_FUZZER): $(DUCKDBLIB) pipe_fuzzer.cpp
	$(CXX) -D DUCKDB_READ_FUNCTION=\"read_csv\" pipe_fuzzer.cpp $(INC) $(CXXFLAGS) $(DUCKDBLIB) $(DUCKDB_DEPS) $(DUCKDB_EXT) -o $(CSV_PIPE_FUZZER)

$(JSON_PIPE_FUZZER): $(DUCKDBLIB) pipe_fuzzer.cpp
	$(CXX) -D DUCKDB_READ_FUNCTION=\"read_json\" pipe_fuzzer.cpp $(INC) $(CXXFLAGS) $(DUCKDBLIB) $(DUCKDB_DEPS) $(DUCKDB_EXT) -o $(JSON_PIPE_FUZZER)


# fuzz attaching DuckDB's native storage format

$(DUCKDB_FILE_FUZZER): $(DUCKDBLIB) duckdb_file_fuzzer.cpp
	$(CXX) duckdb_file_fuzzer.cpp $(INC) $(CXXFLAGS) $(DUCKDBLIB) $(DUCKDB_DEPS) $(DUCKDB_EXT) -o $(DUCKDB_FILE_FUZZER)

.PHONY: all
