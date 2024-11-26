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
CSV_FILE_FUZZER          = $(BUILD_DIR)/csv_file_fuzzer
CSV_FILE_PARMETER_FUZZER = $(BUILD_DIR)/csv_file_parameter_fuzzer
CSV_PIPE_FUZZER          = $(BUILD_DIR)/csv_pipe_fuzzer
JSON_FILE_FUZZER         = $(BUILD_DIR)/json_file_fuzzer
JSON_PIPE_FUZZER         = $(BUILD_DIR)/json_pipe_fuzzer
PARQUET_FILE_FUZZER      = $(BUILD_DIR)/parquet_file_fuzzer
DUCKDB_FILE_FUZZER       = $(BUILD_DIR)/duckdb_file_fuzzer
WAL_FUZZER               = $(BUILD_DIR)/wal_fuzzer

# duckdb version
# DUCKDB_COMMIT_ISH   ?= v1.1.3
DUCKDB_COMMIT_ISH   ?= main

# clones duckdb into AFL++ container
afl-up:
	@open -a Docker
	@sleep 3
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
	docker exec -w / afl-container git clone https://github.com/duckdb/duckdb.git --no-checkout > /dev/null
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
		afl-container \
		make duckdb-lib

re-compile-duckdb: checkout-duckdb
	docker exec -w $(DUCKDB_DIR) afl-container make clean
	docker exec -w $(SRC_DIR) \
		-e CC=/AFLplusplus/afl-clang-fast \
		-e CXX=/AFLplusplus/afl-clang-fast++ \
		afl-container \
		make duckdb-lib

compile-fuzzers: compile-duckdb
	docker exec -w $(SRC_DIR) \
		-e CC=/AFLplusplus/afl-clang-fast \
		-e CXX=/AFLplusplus/afl-clang-fast++ \
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

fuzz-csv-file:
	docker exec afl-container mkdir -p $(RESULT_DIR)/csv_file_fuzzer
	docker exec afl-container find $(DUCKDB_DIR)/data/csv -type f -size +40k -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 3600 \
		-i $(DUCKDB_DIR)/data/csv \
		-o $(RESULT_DIR)/csv_file_fuzzer \
		-m none \
		-d \
		-- $(CSV_FILE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/csv_file_fuzzer fuzz_results

fuzz-csv-file-parameter:
	docker exec afl-container mkdir -p $(RESULT_DIR)/csv_file_parameter_fuzzer
	docker exec afl-container find $(DUCKDB_DIR)/data/csv -type f -size +40k -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 3600 \
		-i $(DUCKDB_DIR)/data/csv \
		-o $(RESULT_DIR)/csv_file_parameter_fuzzer \
		-m none \
		-d \
		-- $(CSV_FILE_PARMETER_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/csv_file_parameter_fuzzer fuzz_results

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

fuzz-json-file:
	docker exec afl-container mkdir -p $(RESULT_DIR)/json_file_fuzzer
	docker exec afl-container find $(DUCKDB_DIR)/data/json -type f -size +40k -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 3600 \
		-i $(DUCKDB_DIR)/data/json \
		-o $(RESULT_DIR)/json_file_fuzzer \
		-m none \
		-d \
		-- $(JSON_FILE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/json_file_fuzzer fuzz_results

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

fuzz-parquet-file:
	docker exec afl-container mkdir -p $(RESULT_DIR)/parquet_fuzzer
	docker exec afl-container find $(DUCKDB_DIR)/data/parquet-testing -type f -size +100k -delete
	docker exec afl-container -w / /AFLplusplus/afl-fuzz \
		-V 3600 \
		-i $(DUCKDB_DIR)/data/parquet-testing \
		-o $(RESULT_DIR)/parquet_fuzzer \
		-m none \
		-d \
		-- $(PARQUET_FILE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/parquet_fuzzer fuzz_results

fuzz-duckdb-file:
	./scripts/create_duckdb_file_corpus.sh "./scripts/duckdb_corpus_init" "./corpus/duckdbfiles"
	docker exec afl-container mkdir -p $(RESULT_DIR)/duckdb_file_fuzzer
	docker cp ./corpus/duckdbfiles afl-container:$(CORPUS_DIR)
	docker exec -w / afl-container /AFLplusplus/afl-fuzz \
		-V 3600 \
		-i $(CORPUS_DIR)/duckdbfiles \
		-o $(RESULT_DIR)/duckdb_file_fuzzer \
		-m none \
		-d \
		-- $(DUCKDB_FILE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/duckdb_file_fuzzer fuzz_results

fuzz-wal-file:
	./scripts/create_wal_file_corpus.sh
	docker exec afl-container mkdir -p $(RESULT_DIR)/wal_fuzzer
	docker cp ./corpus/walfiles afl-container:$(CORPUS_DIR)
	docker cp ./build/base_db afl-container:$(BUILD_DIR)/base_db
	docker exec -w / afl-container /AFLplusplus/afl-fuzz \
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
		fuzz-csv-file fuzz-csv-file-parameter fuzz-csv-pipe fuzz-json-file fuzz-json-pipe fuzz-parquet-file \
		fuzz-duckdb-file fuzz-wal-file \
		man-page format
