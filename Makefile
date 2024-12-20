# local setting (set local path to duckdb repository); only for target 'compile-fuzzers-local'
DUCKDB_LOCAL_DIR ?= ${HOME}/git/duckdb

# container lay-out
DUCKDB_DIR             = /duckdb
DUCKDB_AFLPLUSPLUS_DIR = /duckdb_aflplusplus
SRC_DIR    = $(DUCKDB_AFLPLUSPLUS_DIR)/src
SCRIPT_DIR = $(DUCKDB_AFLPLUSPLUS_DIR)/scripts
BUILD_DIR  = $(DUCKDB_AFLPLUSPLUS_DIR)/build
CORPUS_DIR = $(DUCKDB_AFLPLUSPLUS_DIR)/corpus
RESULT_DIR = $(DUCKDB_AFLPLUSPLUS_DIR)/fuzz_results

# fuzz targets (executables)
CSV_BASE_FUZZER         ?= $(BUILD_DIR)/csv_base_fuzzer
CSV_SINGLE_PARAM_FUZZER ?= $(BUILD_DIR)/csv_single_param_fuzzer
CSV_MULTI_PARAM_FUZZER  ?= $(BUILD_DIR)/csv_multi_param_fuzzer
CSV_PIPE_FUZZER         ?= $(BUILD_DIR)/csv_pipe_fuzzer
JSON_BASE_FUZZER        ?= $(BUILD_DIR)/json_base_fuzzer
JSON_MULTI_PARAM_FUZZER ?= $(BUILD_DIR)/json_multi_param_fuzzer
JSON_PIPE_FUZZER        ?= $(BUILD_DIR)/json_pipe_fuzzer
PARQUET_BASE_FUZZER     ?= $(BUILD_DIR)/parquet_base_fuzzer
DUCKDB_FILE_FUZZER      ?= $(BUILD_DIR)/duckdb_file_fuzzer
WAL_FUZZER              ?= $(BUILD_DIR)/wal_fuzzer

# duckdb version
# DUCKDB_COMMIT_ISH   ?= v1.1.3
DUCKDB_COMMIT_ISH   ?= main

# clones duckdb into AFL++ container
afl-up:
	@open -a docker && while ! docker info > /dev/null 2>&1; do sleep 1 ; done
	@docker pull aflplusplus/aflplusplus > /dev/null
	@docker run --name afl-container  -d \
		aflplusplus/aflplusplus sleep infinity \
		> /dev/null
	@docker exec -w / afl-container mkdir -p duckdb_aflplusplus
	@docker cp src afl-container:$(SRC_DIR) > /dev/null
	@docker cp scripts afl-container:$(SCRIPT_DIR) > /dev/null
	@docker exec afl-container mkdir -p $(BUILD_DIR)
	@docker exec afl-container mkdir -p $(CORPUS_DIR)
	@docker exec afl-container mkdir -p $(RESULT_DIR)
	docker exec -w / afl-container git clone https://github.com/duckdb/duckdb.git --no-checkout
	@docker ps

copy-src-to-container:
	@docker exec afl-container rm -rf $(SRC_DIR) > /dev/null
	@docker cp src afl-container:$(SRC_DIR) > /dev/null

checkout-duckdb:
	docker exec -w $(DUCKDB_DIR) afl-container git checkout main
	docker exec -w $(DUCKDB_DIR) afl-container git pull
	docker exec -w $(DUCKDB_DIR) afl-container git checkout $(DUCKDB_COMMIT_ISH)

compile-duckdb: checkout-duckdb
	docker exec -w $(SRC_DIR) \
		-e CC=/AFLplusplus/afl-clang-fast \
		-e CXX=/AFLplusplus/afl-clang-fast++ \
		-e BUILD_JEMALLOC=1 \
		afl-container \
		make duckdb-lib

re-compile-duckdb: checkout-duckdb
	docker exec -w $(DUCKDB_DIR) afl-container make clean
	docker exec -w $(SRC_DIR) \
		-e CC=/AFLplusplus/afl-clang-fast \
		-e CXX=/AFLplusplus/afl-clang-fast++ \
		-e BUILD_JEMALLOC=1 \
		afl-container \
		make duckdb-lib

compile-fuzzers: copy-src-to-container compile-duckdb
	docker exec -w $(SRC_DIR) \
		-e CC=/AFLplusplus/afl-clang-fast \
		-e CXX=/AFLplusplus/afl-clang-fast++ \
		-e BUILD_JEMALLOC=1 \
		afl-container \
		make all

compile-fuzzers-CI:
	docker exec -w / afl-container git clone https://github.com/duckdb/duckdb.git > /dev/null
	docker exec -w $(SRC_DIR) \
		-e CC=/AFLplusplus/afl-clang-fast \
		-e CXX=/AFLplusplus/afl-clang-fast++ \
		-e BUILD_JEMALLOC=1 \
		afl-container \
		make all

compile-fuzzers-local:
	$(eval ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST)))))
	mkdir -p $(ROOT_DIR)/build
	cd src && DUCKDB_DIR=$(DUCKDB_LOCAL_DIR) DUCKDB_AFLPLUSPLUS_DIR=$(ROOT_DIR) make all

fuzz-csv-base:
	docker exec afl-container mkdir -p $(RESULT_DIR)/csv_base_fuzzer
	docker exec afl-container find $(DUCKDB_DIR)/data/csv -type f -size +40k -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 3600 \
		-i $(DUCKDB_DIR)/data/csv \
		-o $(RESULT_DIR)/csv_base_fuzzer \
		-m none \
		-d \
		-- $(CSV_BASE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/csv_base_fuzzer fuzz_results

fuzz-csv-single-param:
	docker exec afl-container mkdir -p $(RESULT_DIR)/csv_single_param_fuzzer
	docker exec afl-container find $(DUCKDB_DIR)/data/csv -type f -size +40k -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 3600 \
		-i $(DUCKDB_DIR)/data/csv \
		-o $(RESULT_DIR)/csv_single_param_fuzzer \
		-m none \
		-d \
		-- $(CSV_SINGLE_PARAM_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/csv_single_param_fuzzer fuzz_results

fuzz-csv-multi-param:
	$(eval ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST)))))
	$(ROOT_DIR)/scripts/corpus_creation/create_multi_param_corpus_info.py read_csv
	$(ROOT_DIR)/scripts/corpus_creation/create_multi_param_corpus.py read_csv
	docker exec afl-container mkdir -p $(RESULT_DIR)/csv_multi_param_fuzzer
	docker exec afl-container mkdir -p $(CORPUS_DIR)/csv/corpus_prepended
	docker cp $(ROOT_DIR)/corpus/csv/corpus_prepended afl-container:$(CORPUS_DIR)/csv
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 3600 \
		-i $(CORPUS_DIR)/csv/corpus_prepended \
		-o $(RESULT_DIR)/csv_multi_param_fuzzer \
		-m none \
		-d \
		-- $(CSV_MULTI_PARAM_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/csv_multi_param_fuzzer fuzz_results

fuzz-csv-pipe:
	docker exec afl-container mkdir -p $(RESULT_DIR)/csv_pipe_fuzzer
	docker exec afl-container find $(DUCKDB_DIR)/data/csv -type f -size +40k -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 3600 \
		-i $(DUCKDB_DIR)/data/csv \
		-o $(RESULT_DIR)/csv_pipe_fuzzer \
		-m none \
		-d \
		-- $(CSV_PIPE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/csv_pipe_fuzzer fuzz_results

fuzz-json-base:
	docker exec afl-container mkdir -p $(RESULT_DIR)/json_base_fuzzer
	docker exec afl-container find $(DUCKDB_DIR)/data/json -type f -size +40k -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 3600 \
		-i $(DUCKDB_DIR)/data/json \
		-o $(RESULT_DIR)/json_base_fuzzer \
		-m none \
		-d \
		-- $(JSON_BASE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/json_base_fuzzer fuzz_results

fuzz-json-multi-param:
	$(eval ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST)))))
	$(ROOT_DIR)/scripts/corpus_creation/create_multi_param_corpus_info.py read_json
	$(ROOT_DIR)/scripts/corpus_creation/create_multi_param_corpus.py read_json
	docker exec afl-container mkdir -p $(RESULT_DIR)/json_multi_param_fuzzer
	docker exec afl-container mkdir -p $(CORPUS_DIR)/json/corpus_prepended
	docker cp $(ROOT_DIR)/corpus/json/corpus_prepended afl-container:$(CORPUS_DIR)/json
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 3600 \
		-i $(CORPUS_DIR)/json/corpus_prepended \
		-o $(RESULT_DIR)/json_multi_param_fuzzer \
		-m none \
		-d \
		-- $(JSON_MULTI_PARAM_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/json_multi_param_fuzzer fuzz_results

fuzz-json-pipe:
	docker exec afl-container mkdir -p $(RESULT_DIR)/json_pipe_fuzzer
	docker exec afl-container find $(DUCKDB_DIR)/data/json -type f -size +40k -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 3600 \
		-i $(DUCKDB_DIR)/data/json \
		-o $(RESULT_DIR)/json_pipe_fuzzer \
		-m none \
		-d \
		-- $(JSON_PIPE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/json_pipe_fuzzer fuzz_results

fuzz-parquet-base:
	docker exec afl-container mkdir -p $(RESULT_DIR)/parquet_base_fuzzer
	docker exec afl-container find $(DUCKDB_DIR)/data/parquet-testing -type f -size +100k -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 3600 \
		-i $(DUCKDB_DIR)/data/parquet-testing \
		-o $(RESULT_DIR)/parquet_base_fuzzer \
		-m none \
		-d \
		-- $(PARQUET_BASE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/parquet_base_fuzzer fuzz_results

fuzz-duckdb-file:
	./scripts/corpus_creation/create_duckdb_file_corpus.sh "./scripts/corpus_creation/duckdb_corpus_init" "./corpus/duckdbfiles"
	docker exec afl-container mkdir -p $(RESULT_DIR)/duckdb_file_fuzzer
	docker cp ./corpus/duckdbfiles afl-container:$(CORPUS_DIR)
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 3600 \
		-i $(CORPUS_DIR)/duckdbfiles \
		-o $(RESULT_DIR)/duckdb_file_fuzzer \
		-m none \
		-d \
		-- $(DUCKDB_FILE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/duckdb_file_fuzzer fuzz_results

fuzz-wal-file:
	./scripts/corpus_creation/create_wal_file_corpus.sh
	docker exec afl-container mkdir -p $(RESULT_DIR)/wal_fuzzer
	docker cp ./corpus/walfiles afl-container:$(CORPUS_DIR)
	docker cp ./build/base_db afl-container:$(BUILD_DIR)/base_db
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 3600 \
		-i $(CORPUS_DIR)/walfiles \
		-o $(RESULT_DIR)/wal_fuzzer \
		-m none \
		-d \
		-- $(WAL_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/wal_fuzzer fuzz_results

# removes container, but not the image
afl-down:
	@docker stop -t0 afl-container
	@docker system prune -f > /dev/null

man-page:
	@docker exec afl-container afl-fuzz -hh || true

format:
	find src -name "*.cpp" -o -name "*.hpp" | xargs clang-format -i --sort-includes=0 -style=file

.PHONY: afl-up compile-fuzzers afl-down \
		fuzz-csv-base fuzz-csv-single-param fuzz-csv-multi-param fuzz-csv-pipe \
		fuzz-json-base fuzz-json-pipe fuzz-json-multi-param fuzz-parquet-base \
		fuzz-duckdb-file fuzz-wal-file \
		man-page format
