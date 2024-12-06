# container lay-out
DUCKDB_DIR             ?= /duckdb
DUCKDB_AFLPLUSPLUS_DIR ?= /duckdb_aflplusplus

SRC_DIR    ?= $(DUCKDB_AFLPLUSPLUS_DIR)/src
SCRIPT_DIR ?= $(DUCKDB_AFLPLUSPLUS_DIR)/scripts
BUILD_DIR  ?= $(DUCKDB_AFLPLUSPLUS_DIR)/build
CORPUS_DIR ?= $(DUCKDB_AFLPLUSPLUS_DIR)/corpus
RESULT_DIR ?= $(DUCKDB_AFLPLUSPLUS_DIR)/fuzz_results

# fuzz targets (executables)
CSV_FILE_FUZZER               ?= $(BUILD_DIR)/csv_file_fuzzer
CSV_FILE_PARMETER_FUZZER      ?= $(BUILD_DIR)/csv_file_parameter_fuzzer
CSV_FILE_PARMETER_FLEX_FUZZER ?= $(BUILD_DIR)/csv_file_parameter_flex_fuzzer
CSV_PIPE_FUZZER               ?= $(BUILD_DIR)/csv_pipe_fuzzer
JSON_FILE_FUZZER              ?= $(BUILD_DIR)/json_file_fuzzer
JSON_PIPE_FUZZER              ?= $(BUILD_DIR)/json_pipe_fuzzer
PARQUET_FILE_FUZZER           ?= $(BUILD_DIR)/parquet_file_fuzzer
DUCKDB_FILE_FUZZER            ?= $(BUILD_DIR)/duckdb_file_fuzzer
WAL_FUZZER                    ?= $(BUILD_DIR)/wal_fuzzer

CC  ?= /AFLplusplus/afl-clang-fast
CXX ?= /AFLplusplus/afl-clang-fast++

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
	$(DUCKDB_DIR)/build/release/third_party/yyjson/libduckdb_yyjson.a \
	$(DUCKDB_DIR)/build/release/third_party/zstd/libduckdb_zstd.a

DUCKDB_EXT= $(DUCKDB_DIR)/build/release/extension/core_functions/libcore_functions_extension.a \
	$(DUCKDB_DIR)/build/release/extension/parquet/libparquet_extension.a \
	$(DUCKDB_DIR)/build/release/extension/json/libjson_extension.a

INC =-I$(DUCKDB_DIR)/src/include
CXXFLAGS = -std=c++11 -DDUCKDB_DIR=\"$(DUCKDB_DIR)\" -DDUCKDB_AFLPLUSPLUS_DIR=\"$(DUCKDB_AFLPLUSPLUS_DIR)\"

ifeq (${BUILD_JEMALLOC}, 1)
	CXXFLAGS:=${CXXFLAGS} -DBUILD_JEMALLOC=1
	DUCKDB_EXT:=${DUCKDB_EXT} $(DUCKDB_DIR)/build/release/extension/jemalloc/libjemalloc_extension.a
endif

all: $(CSV_FILE_FUZZER) $(CSV_FILE_PARMETER_FUZZER) $(CSV_FILE_PARMETER_FLEX_FUZZER) $(CSV_PIPE_FUZZER) $(JSON_FILE_FUZZER) $(JSON_PIPE_FUZZER) $(PARQUET_FILE_FUZZER) $(DUCKDB_FILE_FUZZER) $(WAL_FUZZER)

duckdb-lib: $(DUCKDBLIB)

$(DUCKDBLIB):
	cd $(DUCKDB_DIR) && CC=$(CC) CXX=$(CXX) GEN=ninja BUILD_JSON=1 CRASH_ON_ASSERT=1 make


# file reader fuzzers (csv, json, parquet)

$(CSV_FILE_FUZZER): $(DUCKDBLIB) file_reader_fuzzer.cpp
	$(CXX) -D DUCKDB_READ_FUNCTION=\"read_csv\" file_reader_fuzzer.cpp $(INC) $(CXXFLAGS) $(DUCKDBLIB) $(DUCKDB_EXT) $(DUCKDB_DEPS) -o $(CSV_FILE_FUZZER)

$(CSV_FILE_PARMETER_FUZZER): $(DUCKDBLIB) csv_parameter_fuzzer.cpp
	$(CXX) -D DUCKDB_READ_FUNCTION=\"read_csv\" csv_parameter_fuzzer.cpp $(INC) $(CXXFLAGS) $(DUCKDBLIB) $(DUCKDB_EXT) $(DUCKDB_DEPS) -o $(CSV_FILE_PARMETER_FUZZER)

$(CSV_FILE_PARMETER_FLEX_FUZZER): $(DUCKDBLIB) csv_parameter_flex_fuzzer.cpp
	$(CXX) -D DUCKDB_READ_FUNCTION=\"read_csv\" csv_parameter_flex_fuzzer.cpp $(INC) $(CXXFLAGS) $(DUCKDBLIB) $(DUCKDB_EXT) $(DUCKDB_DEPS) -o $(CSV_FILE_PARMETER_FLEX_FUZZER)

$(JSON_FILE_FUZZER): $(DUCKDBLIB) file_reader_fuzzer.cpp
	$(CXX) -D DUCKDB_READ_FUNCTION=\"read_json\" file_reader_fuzzer.cpp $(INC) $(CXXFLAGS) $(DUCKDBLIB) $(DUCKDB_EXT) $(DUCKDB_DEPS) -o $(JSON_FILE_FUZZER)

$(PARQUET_FILE_FUZZER): $(DUCKDBLIB) file_reader_fuzzer.cpp
	$(CXX) -D DUCKDB_READ_FUNCTION=\"read_parquet\" file_reader_fuzzer.cpp $(INC) $(CXXFLAGS) $(DUCKDBLIB) $(DUCKDB_EXT) $(DUCKDB_DEPS) -o $(PARQUET_FILE_FUZZER)


# pipe fuzzers (csv, json)

$(CSV_PIPE_FUZZER): $(DUCKDBLIB) pipe_fuzzer.cpp
	$(CXX) -D DUCKDB_READ_FUNCTION=\"read_csv\" pipe_fuzzer.cpp $(INC) $(CXXFLAGS) $(DUCKDBLIB) $(DUCKDB_EXT) $(DUCKDB_DEPS) -o $(CSV_PIPE_FUZZER)

$(JSON_PIPE_FUZZER): $(DUCKDBLIB) pipe_fuzzer.cpp
	$(CXX) -D DUCKDB_READ_FUNCTION=\"read_json\" pipe_fuzzer.cpp $(INC) $(CXXFLAGS) $(DUCKDBLIB) $(DUCKDB_EXT) $(DUCKDB_DEPS) -o $(JSON_PIPE_FUZZER)


# fuzz attaching DuckDB's native storage format

$(DUCKDB_FILE_FUZZER): $(DUCKDBLIB) duckdb_file_fuzzer.cpp
	$(CXX) duckdb_file_fuzzer.cpp $(INC) $(CXXFLAGS) $(DUCKDBLIB) $(DUCKDB_EXT) $(DUCKDB_DEPS) -o $(DUCKDB_FILE_FUZZER)


# wal file fuzzer

$(WAL_FUZZER): $(DUCKDBLIB) wal_fuzzer.cpp
	$(CXX) wal_fuzzer.cpp $(INC) $(CXXFLAGS) $(DUCKDBLIB) $(DUCKDB_EXT) $(DUCKDB_DEPS) -o $(WAL_FUZZER)

.PHONY: all duckdb-lib
