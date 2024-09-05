NAME=csv_fuzzer

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

all: $(NAME)

$(NAME): csv_fuzz.o $(DUCKDBLIB)
	$(CXX) csv_fuzz.o $(DUCKDBLIB) $(DUCKDB_DEPS) $(DUCKDB_EXT) -o $(NAME)

csv_fuzz.o: csv_fuzz.cpp
	$(CXX) $(INC) $(CXXFLAGS) -c $< -o $@

$(DUCKDBLIB):
	cd $(DUCKDB_DIR) && CC=$(CC) CXX=$(CXX) GEN=ninja BUILD_JSON=1 make

clean:
	rm -f csv_fuzzer
	rm -f csv_fuzz.o
	rm -f temp_csv_input.csv
