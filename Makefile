# !! requires docker desktop to run locally !!

# container lay-out
SRC_DIR=/duckdb_aflplusplus/src
SCRIPT_DIR=/duckdb_aflplusplus/scripts
BUILD_DIR=/duckdb_aflplusplus/build
CORPUS_DIR=/duckdb_aflplusplus/corpus
RESULT_DIR=/duckdb_aflplusplus/fuzz_results

# fuzz targets (executables)
CSV_FILE_FUZZER=$(BUILD_DIR)/csv_file_fuzzer
CSV_PIPE_FUZZER=$(BUILD_DIR)/csv_pipe_fuzzer
JSON_FILE_FUZZER=$(BUILD_DIR)/json_file_fuzzer
JSON_PIPE_FUZZER=$(BUILD_DIR)/json_pipe_fuzzer
PARQUET_FILE_FUZZER=$(BUILD_DIR)/parquet_file_fuzzer
DUCKDB_FILE_FUZZER=$(BUILD_DIR)/duckdb_file_fuzzer
WAL_FUZZER=$(BUILD_DIR)/wal_fuzzer

# clones duckdb into AFL++ container
afl-up:
	@open -a Docker
	@sleep 2
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
	@docker ps

compile-fuzzers:
	docker exec -w / afl-container git clone https://github.com/duckdb/duckdb.git > /dev/null
	docker exec -w $(SRC_DIR) afl-container make $(CSV_FILE_FUZZER) CSV_FILE_FUZZER=$(CSV_FILE_FUZZER)
	docker exec -w $(SRC_DIR) afl-container make $(CSV_PIPE_FUZZER) CSV_PIPE_FUZZER=$(CSV_PIPE_FUZZER)
	docker exec -w $(SRC_DIR) afl-container make $(JSON_FILE_FUZZER) JSON_FILE_FUZZER=$(JSON_FILE_FUZZER)
	docker exec -w $(SRC_DIR) afl-container make $(JSON_PIPE_FUZZER) JSON_PIPE_FUZZER=$(JSON_PIPE_FUZZER)
	docker exec -w $(SRC_DIR) afl-container make $(PARQUET_FILE_FUZZER) PARQUET_FILE_FUZZER=$(PARQUET_FILE_FUZZER)
	docker exec -w $(SRC_DIR) afl-container make $(DUCKDB_FILE_FUZZER) DUCKDB_FILE_FUZZER=$(DUCKDB_FILE_FUZZER)
	docker exec -w $(SRC_DIR) afl-container make $(WAL_FUZZER) WAL_FUZZER=$(WAL_FUZZER)

fuzz-csv-file:
	docker exec afl-container mkdir -p $(RESULT_DIR)/csv_file_fuzzer
	docker exec afl-container find /duckdb/data/csv -type f -size +40k -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 10 \
		-i /duckdb/data/csv \
		-o $(RESULT_DIR)/csv_file_fuzzer \
		-m none \
		-d \
		-- $(CSV_FILE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/csv_file_fuzzer fuzz_results

fuzz-csv-pipe:
	docker exec afl-container mkdir -p $(RESULT_DIR)/csv_pipe_fuzzer
	docker exec afl-container find /duckdb/data/csv -type f -size +40k -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 10 \
		-i /duckdb/data/csv \
		-o $(RESULT_DIR)/csv_pipe_fuzzer \
		-m none \
		-d \
		-- $(CSV_PIPE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/csv_pipe_fuzzer fuzz_results

fuzz-json-file:
	docker exec afl-container mkdir -p $(RESULT_DIR)/json_file_fuzzer
	docker exec afl-container find /duckdb/data/json -type f -size +40k -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 10 \
		-i /duckdb/data/json \
		-o $(RESULT_DIR)/json_file_fuzzer \
		-m none \
		-d \
		-- $(JSON_FILE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/json_file_fuzzer fuzz_results

fuzz-json-pipe:
	docker exec afl-container mkdir -p $(RESULT_DIR)/json_pipe_fuzzer
	docker exec afl-container find /duckdb/data/json -type f -size +40k -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 10 \
		-i /duckdb/data/json \
		-o $(RESULT_DIR)/json_pipe_fuzzer \
		-m none \
		-d \
		-- $(JSON_PIPE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/json_pipe_fuzzer fuzz_results

fuzz-parquet-file:
	docker exec afl-container mkdir -p $(RESULT_DIR)/parquet_fuzzer
	docker exec afl-container find /duckdb/data/parquet-testing -type f -size +100k -delete
	docker exec afl-container -w / /AFLplusplus/afl-fuzz \
		-V 10 \
		-i /duckdb/data/parquet-testing \
		-o $(RESULT_DIR)/parquet_fuzzer \
		-m none \
		-d \
		-- $(PARQUET_FILE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/parquet_fuzzer fuzz_results

fuzz-duckdb-file:
	./scripts/create_duckdb_file_corpus.sh
	docker exec afl-container mkdir -p $(RESULT_DIR)/duckdb_file_fuzzer
	docker cp ./corpus/duckdbfiles afl-container:$(CORPUS_DIR)
	docker exec -w / afl-container /AFLplusplus/afl-fuzz \
		-V 10 \
		-i $(CORPUS_DIR)/duckdbfiles \
		-o $(RESULT_DIR)/duckdb_file_fuzzer \
		-m none \
		-d \
		-- $(DUCKDB_FILE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:$(RESULT_DIR)/duckdb_file_fuzzer fuzz_results

fuzz-wall-file:
	./scripts/create_wal_file_corpus.sh
	docker exec afl-container mkdir -p $(RESULT_DIR)/wal_fuzzer
	docker cp ./corpus/walfiles afl-container:$(CORPUS_DIR)
	docker cp ./build/base_db afl-container:$(BUILD_DIR)/base_db
	docker exec -w / afl-container /AFLplusplus/afl-fuzz \
		-V 10 \
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
		fuzz-csv-file fuzz-csv-pipe fuzz-json-file fuzz-json-pipe fuzz-parquet-file \
		fuzz-duckdb-file fuzz-wall-file \
		afl-down man-page format
