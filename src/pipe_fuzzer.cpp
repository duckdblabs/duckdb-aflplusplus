#include "duckdb.hpp"

#include <iostream>
#include <string>
#include <unistd.h>

void PipeFuzzer(std::string file_read_function) {
	/*
	Move data from stdin to dataPipe, so duckdb can read from it.
	This is needed because duckdb checks the fd for S_ISFIFO.
	example:
	  $ cat flights.csv | duckdb -c "SELECT * FROM read_csv('/dev/stdin')"
	*/
	uint8_t buf[4096];
	int dataPipe[2];
	if (pipe(dataPipe) < 0) {
		perror(NULL);
		exit(1);
	}
	int nRead = 1;
	while (nRead != 0) {
		nRead = read(STDIN_FILENO, (void *)buf, 4096);
		if (nRead < 0) {
			perror(NULL);
			exit(1);
		}
		if (write(dataPipe[1], (void *)buf, nRead) < 0) {
			perror(NULL);
			exit(1);
		}
	}
	if (close(dataPipe[1]) < 0) {
		perror(NULL);
		exit(1);
	}

	// redirect stdin to pipe
	if (dup2(dataPipe[0], STDIN_FILENO) < 0) {
		perror(NULL);
		exit(1);
	}

	// ingest data (to test if it crashes duckdb)
	duckdb::DuckDB db(nullptr);
	duckdb::Connection con(db);
	std::string query = "SELECT * FROM " + file_read_function + "('/dev/stdin');";
	duckdb::unique_ptr<duckdb::MaterializedQueryResult> q_result = con.Query(query);
	// std::cout << q_result->ToString() << std::endl;

	if (close(dataPipe[0]) < 0) {
		perror(NULL);
		exit(1);
	}
}

int main() {
#ifdef DUCKDB_READ_FUNCTION
	std::string file_read_function = DUCKDB_READ_FUNCTION;
	if (file_read_function != "read_csv" && file_read_function != "read_json") {
		std::cerr << "function '" + file_read_function + "' is not supported" << std::endl;
		exit(1);
	}
	PipeFuzzer(file_read_function);
#else
	std::cerr << "read function to fuzz not specified!" << std::endl;
	exit(1);
#endif
	return 0;
}
