#include "duckdb.hpp"
#include <iostream>
#include <unistd.h>

const int NR_SCENARIO_BYTES = 0;
const int BUFF_SIZE = 4096;

void AppenderFuzzer() {
	duckdb::DuckDB db(nullptr);
	duckdb::Connection con(db);

	uint8_t buf[4096];

	// read scenario bytes
	// TODO: e.g. use NULL instead of empty string
	uint8_t scenario_buf[NR_SCENARIO_BYTES];
	read(0, (void *)scenario_buf, NR_SCENARIO_BYTES);

	int n_read = 1;
	int idx_buf;
	int idx_start_char;
	std::string val1;
	std::string val2;
	bool reading_first_val = true;

	// append records (read from stdin)
	con.Query("CREATE OR REPLACE TABLE tbl (col1 VARCHAR, col2 VARCHAR)");
	duckdb::Appender appender(con, "tbl");
	while (n_read != 0) {
		n_read = read(0, (void *)buf, BUFF_SIZE);
		if (n_read < 0) {
			std::cout << "error in read: " << n_read << std::endl;
			perror(NULL);
			exit(EXIT_FAILURE);
		}

		// split rows by newline, split values by comma (if any)
		idx_buf = 0;
		idx_start_char = 0;
		while (idx_buf < n_read) {
			if (buf[idx_buf] == ',' && reading_first_val) {
				val1 = val1 + std::string(reinterpret_cast<const char*>(buf + idx_start_char), idx_buf - idx_start_char);
				idx_start_char = idx_buf + 1;
				reading_first_val = false;
			}
			if (buf[idx_buf] == '\n') {
				if (reading_first_val) {
					val1 = val1 + std::string(reinterpret_cast<const char*>(buf + idx_start_char), idx_buf - idx_start_char);
				} else {
					val2 = val2 + std::string(reinterpret_cast<const char*>(buf + idx_start_char), idx_buf - idx_start_char);
				}
				// add row
				appender.AppendRow(val1.c_str(), val2.c_str());
				// reset
				val1 = "";
				val2 = "";
				reading_first_val = true;
				idx_start_char = idx_buf + 1;
			}
			// end of read-buffer, preserve what we have so far
			if (idx_buf == n_read - 1) {
				if (reading_first_val == true) {
					val1 = val1 + std::string(reinterpret_cast<const char*>(buf + idx_start_char), idx_buf + 1 - idx_start_char);
				} else {
					val2 = val2 + std::string(reinterpret_cast<const char*>(buf + idx_start_char), idx_buf + 1 - idx_start_char);
				}
			}
			idx_buf++;
		}
	}
	// add final row
	if (val1 != "") {
		appender.AppendRow(val1.c_str(), val2.c_str());
	}
	// flush
	appender.Close();

	// debug
	// duckdb::unique_ptr<duckdb::QueryResult> result;
	// result = con.Query("FROM tbl");
	// std::cout << result->ToString() << std::endl;
	// std::cout << con.Query("SELECT count(*) FROM tbl")->ToString() << std::endl;
}

int main() {
	try {
		AppenderFuzzer();
	} catch (duckdb::InvalidInputException) {
	}
}
