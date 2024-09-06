# !! requires docker desktop to run locally !!

CSV_FUZZER=csv_fuzzer
JSON_FUZZER=json_fuzzer

# clones duckdb into AFL++ container
afl-up:
	@open -a Docker
	@mkdir -p ./fuzztests/fuzz_results_csv_reader
	@mkdir -p ./fuzztests/fuzz_results_json_reader
	@docker pull aflplusplus/aflplusplus > /dev/null
	@docker run --name afl-container  -d \
		-v ./fuzztests:/fuzztests \
		aflplusplus/aflplusplus sleep infinity \
		> /dev/null
	@docker exec -w / afl-container git clone https://github.com/duckdb/duckdb.git > /dev/null
	@docker ps

compile-csv:
	docker exec -w /fuzztests afl-container make $(CSV_FUZZER) CSV_FUZZER=$(CSV_FUZZER)

compile-json:
	docker exec -w /fuzztests afl-container make $(JSON_FUZZER) JSON_FUZZER=$(JSON_FUZZER)

fuzz-csv-reader:
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 100 \
		-i /duckdb/data/csv \
		-o /fuzztests/fuzz_results_csv_reader \
		-m none \
		-d \
		-- /fuzztests/$(CSV_FUZZER)

fuzz-json-reader:
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 100 \
		-i /duckdb/data/json \
		-o /fuzztests/fuzz_results_json_reader \
		-m none \
		-d \
		-- /fuzztests/$(JSON_FUZZER)

# removes container, but not the image
afl-down:
	@docker stop -t0 afl-container
	@docker system prune -f > /dev/null
	@rm -f ./fuzztests/csv_fuzzer
	@rm -f ./fuzztests/csv_fuzz.o
	@rm -f ./fuzztests/json_fuzzer
	@rm -f ./fuzztests/json_fuzz.o

man-page:
	@docker exec afl-container afl-fuzz -hh || true

.PHONY: afl-up compile-csv compile-json afl-down fuzz-csv-reader fuzz-json-reader afl-down man-page
