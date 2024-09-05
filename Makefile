# requires docker desktop to run locally

# clones duckdb into AFL++ container
afl-up:
	@open -a Docker
	@docker pull aflplusplus/aflplusplus > /dev/null
	@docker run --name afl-container  -d \
		-v ./fuzztest_csv:/fuzztest_csv \
		-v ./fuzz_results:/fuzz_results \
		aflplusplus/aflplusplus sleep infinity \
		> /dev/null
	@docker exec -w / afl-container git clone https://github.com/duckdb/duckdb.git
	@docker ps

# creates a fuzzable DuckDB executable with AFL++ compiler, in the AFL++ container
afl-compile:
	docker exec -w /fuzztest_csv afl-container make

# runs afl-fuzz
afl-run:
	echo "start fuzzing..."
	docker exec afl-container /AFLplusplus/afl-fuzz \
		-V 10 \
		-i /duckdb/data/csv \
		-o /fuzz_results \
		-m none \
		-d \
		-- /fuzztest_csv/csv_fuzzer

# remove container, but not the image
afl-clean:
	@docker stop -t0 afl-container
	@docker system prune -f > /dev/null

.PHONY: afl-up afl-compile afl-run afl-clean
