# !! requires docker desktop to run locally !!

CSV_FILE_FUZZER=csv_file_fuzzer
CSV_PIPE_FUZZER=csv_pipe_fuzzer
JSON_FILE_FUZZER=json_file_fuzzer
JSON_PIPE_FUZZER=json_pipe_fuzzer
PARQUET_FILE_FUZZER=parquet_file_fuzzer

# clones duckdb into AFL++ container
afl-up:
	@open -a Docker
	@docker pull aflplusplus/aflplusplus > /dev/null
	@docker run --name afl-container  -d \
		aflplusplus/aflplusplus sleep infinity \
		> /dev/null
	@docker cp src afl-container:/fuzz_src > /dev/null
	@docker ps

compile-fuzzers:
	docker exec -w / afl-container git clone https://github.com/duckdb/duckdb.git > /dev/null
	docker exec -w /fuzz_src afl-container make $(CSV_FILE_FUZZER) CSV_FILE_FUZZER=$(CSV_FILE_FUZZER)
	docker exec -w /fuzz_src afl-container make $(CSV_PIPE_FUZZER) CSV_PIPE_FUZZER=$(CSV_PIPE_FUZZER)
	docker exec -w /fuzz_src afl-container make $(JSON_FILE_FUZZER) JSON_FILE_FUZZER=$(JSON_FILE_FUZZER)
	docker exec -w /fuzz_src afl-container make $(JSON_PIPE_FUZZER) JSON_PIPE_FUZZER=$(JSON_PIPE_FUZZER)
	docker exec -w /fuzz_src afl-container make $(PARQUET_FILE_FUZZER) PARQUET_FILE_FUZZER=$(PARQUET_FILE_FUZZER)

fuzz-csv-file:
	docker exec afl-container mkdir -p /fuzz_results/$(CSV_FILE_FUZZER)
	docker exec afl-container find /duckdb/data/csv -type f -size +40k -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 10 \
		-i /duckdb/data/csv \
		-o /fuzz_results/$(CSV_FILE_FUZZER) \
		-m none \
		-d \
		-- /fuzz_src/$(CSV_FILE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:/fuzz_results/$(CSV_FILE_FUZZER) fuzz_results

fuzz-csv-pipe:
	docker exec afl-container mkdir -p /fuzz_results/$(CSV_PIPE_FUZZER)
	docker exec afl-container find /duckdb/data/csv -type f -size +40k -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 10 \
		-i /duckdb/data/csv \
		-o /fuzz_results/$(CSV_PIPE_FUZZER) \
		-m none \
		-d \
		-- /fuzz_src/$(CSV_PIPE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:/fuzz_results/$(CSV_PIPE_FUZZER) fuzz_results

fuzz-json-file:
	docker exec afl-container mkdir -p /fuzz_results/$(JSON_FILE_FUZZER)
	docker exec afl-container find /duckdb/data/json -type f -size +40k -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 10 \
		-i /duckdb/data/json \
		-o /fuzz_results/$(JSON_FILE_FUZZER) \
		-m none \
		-d \
		-- /fuzz_src/$(JSON_FILE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:/fuzz_results/$(JSON_FILE_FUZZER) fuzz_results

fuzz-json-pipe:
	docker exec afl-container mkdir -p /fuzz_results/$(JSON_PIPE_FUZZER)
	docker exec afl-container find /duckdb/data/json -type f -size +40k -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 10 \
		-i /duckdb/data/json \
		-o /fuzz_results/$(JSON_PIPE_FUZZER) \
		-m none \
		-d \
		-- /fuzz_src/$(JSON_PIPE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:/fuzz_results/$(JSON_PIPE_FUZZER) fuzz_results

fuzz-parquet-file:
	docker exec afl-container mkdir -p /fuzz_results/$(PARQUET_FILE_FUZZER)
	docker exec afl-container find /duckdb/data/parquet-testing -type f -size +100k -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 10 \
		-i /duckdb/data/parquet-testing \
		-o /fuzz_results/$(PARQUET_FILE_FUZZER) \
		-m none \
		-d \
		-- /fuzz_src/$(PARQUET_FILE_FUZZER)
	mkdir -p fuzz_results/
	docker cp afl-container:/fuzz_results/$(PARQUET_FILE_FUZZER) fuzz_results

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
		afl-down man-page format
