#include "duckdb.hpp"

#include <fcntl.h>
#include <iostream>
#include <string>
#include <unistd.h>

int main() {
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
	std::string query = "ATTACH '" + filename + "' AS tmp_db (READ_ONLY); use tmp_db; show tables;";
	duckdb::unique_ptr<duckdb::MaterializedQueryResult> q_result = con.Query(query);
	std::cout << q_result->ToString() << std::endl;
}
