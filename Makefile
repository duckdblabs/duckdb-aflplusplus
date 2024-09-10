# !! requires docker desktop to run locally !!

CSV_FILE_FUZZER=csv_file_fuzzer
CSV_FIFO_FUZZER=csv_fifo_fuzzer
JSON_FILE_FUZZER=json_file_fuzzer
JSON_FIFO_FUZZER=json_fifo_fuzzer
PARQUET_FILE_FUZZER=parquet_file_fuzzer

# clones duckdb into AFL++ container
afl-up:
	@open -a Docker
	@docker pull aflplusplus/aflplusplus > /dev/null
	@docker run --name afl-container  -d \
		-v ./fuzztests:/fuzztests \
		aflplusplus/aflplusplus sleep infinity \
		> /dev/null
	@docker exec -w / afl-container git clone https://github.com/duckdb/duckdb.git > /dev/null
	@docker ps

compile-fuzzers:
	docker exec -w /fuzztests afl-container make $(CSV_FILE_FUZZER) CSV_FILE_FUZZER=$(CSV_FILE_FUZZER)
	docker exec -w /fuzztests afl-container make $(CSV_FIFO_FUZZER) CSV_FIFO_FUZZER=$(CSV_FIFO_FUZZER)
	docker exec -w /fuzztests afl-container make $(JSON_FILE_FUZZER) JSON_FILE_FUZZER=$(JSON_FILE_FUZZER)
	docker exec -w /fuzztests afl-container make $(JSON_FIFO_FUZZER) JSON_FIFO_FUZZER=$(JSON_FIFO_FUZZER)
	docker exec -w /fuzztests afl-container make $(PARQUET_FILE_FUZZER) PARQUET_FILE_FUZZER=$(PARQUET_FILE_FUZZER)

fuzz-csv-file:
	@mkdir -p ./fuzztests/results_$(CSV_FILE_FUZZER)
	docker exec afl-container find /duckdb/data/csv -type f -size +10000 -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 10 \
		-i /duckdb/data/csv \
		-o /fuzztests/results_$(CSV_FILE_FUZZER) \
		-m none \
		-d \
		-- /fuzztests/$(CSV_FILE_FUZZER)

fuzz-csv-fifo:
	@mkdir -p ./fuzztests/results_$(CSV_FIFO_FUZZER)
	docker exec afl-container find /duckdb/data/csv -type f -size +10000 -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 10 \
		-i /duckdb/data/csv \
		-o /fuzztests/results_$(CSV_FIFO_FUZZER) \
		-m none \
		-d \
		-- /fuzztests/$(CSV_FIFO_FUZZER)

fuzz-json-file:
	@mkdir -p ./fuzztests/results_$(JSON_FILE_FUZZER)
	docker exec afl-container find /duckdb/data/json -type f -size +10000 -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 10 \
		-i /duckdb/data/json \
		-o /fuzztests/results_$(JSON_FILE_FUZZER) \
		-m none \
		-d \
		-- /fuzztests/$(JSON_FILE_FUZZER)

fuzz-json-fifo:
	@mkdir -p ./fuzztests/results_$(JSON_FIFO_FUZZER)
	docker exec afl-container find /duckdb/data/json -type f -size +10000 -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 10 \
		-i /duckdb/data/json \
		-o /fuzztests/results_$(JSON_FIFO_FUZZER) \
		-m none \
		-d \
		-- /fuzztests/$(JSON_FIFO_FUZZER)

fuzz-parquet-file:
	@mkdir -p ./fuzztests/results_$(PARQUET_FILE_FUZZER)
	docker exec afl-container find /duckdb/data/parquet-testing -type f -size +40000 -delete
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 10 \
		-i /duckdb/data/parquet-testing \
		-o /fuzztests/results_$(PARQUET_FILE_FUZZER) \
		-m none \
		-d \
		-- /fuzztests/$(PARQUET_FILE_FUZZER)

# removes container, but not the image
afl-down:
	@docker stop -t0 afl-container
	@docker system prune -f > /dev/null
	@rm -f ./fuzztests/csv_fuzzer
	@rm -f ./fuzztests/csv_fuzz.o
	@rm -f ./fuzztests/json_fuzzer
	@rm -f ./fuzztests/json_fuzz.o
	@rm -f ./fuzztests/parquet_fuzzer
	@rm -f ./fuzztests/parquet_fuzz.o

man-page:
	@docker exec afl-container afl-fuzz -hh || true

.PHONY: afl-up compile-fuzzers afl-down \
		fuzz-csv-file fuzz-csv-fifo fuzz-json-file fuzz-json-fifo fuzz-parquet-file \
		afl-down man-page
