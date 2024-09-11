#include "duckdb.hpp"

#include <fcntl.h>
#include <iostream>
#include <string>
#include <unistd.h>

void FileReaderFuzzer(std::string filereadFunction) {
	uint8_t buf[4096];

	// create file from stdin
	std::string filename = "temp_input_file";
	int fd = open(filename.c_str(), O_CREAT | O_WRONLY | O_TRUNC, S_IRUSR | S_IWUSR);
	if (fd < 0) {
		std::cerr << "can't create data file: " << filename << std::endl;
		exit(1);
	}
	ssize_t n;
	while (true) {
		n = read(0, (void *)buf, 4096);
		write(fd, (void *)buf, n);
		if (n == 0) {
			break;
		}
	}
	close(fd);

	// ingest file (to test if it crashes duckdb)
	duckdb::DuckDB db(nullptr);
	duckdb::Connection con(db);
	std::string query = "SELECT * FROM " + filereadFunction + "('" + filename + "');";
	duckdb::unique_ptr<duckdb::MaterializedQueryResult> q_result = con.Query(query);
	// std::cout << q_result->ToString() << std::endl;
}

int main() {
#ifdef DUCKDB_READ_FUNCTION
	std::string filereadFunction = DUCKDB_READ_FUNCTION;
	if (filereadFunction != "read_csv" && filereadFunction != "read_json" && filereadFunction != "read_parquet") {
		std::cerr << "function '" + filereadFunction + "' is not supported" << std::endl;
		exit(1);
	}
	FileReaderFuzzer(filereadFunction);
#else
	std::cerr << "duckdb read function to fuzz not specified!" << std::endl;
	exit(1);
#endif
	return 0;
}
