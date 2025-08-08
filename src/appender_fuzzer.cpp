#include "duckdb.hpp"

#include <cassert>
#include <iostream>
#include <unistd.h>

const int NR_SCENARIO_BYTES = 3;
const int BUFF_SIZE = 4096;

void AppenderFuzzer() {
	duckdb::DuckDB db(nullptr);
	duckdb::Connection con(db);

	uint8_t buf[4096];
	uint8_t scenario_buf[NR_SCENARIO_BYTES];

	enum read_state_option {
    	SCENARIO_BYTES,
    	FIRST_VAL,
    	SECOND_VAL
	};

	int n_read = 1;
	int idx_buf;
	int idx_scenario_byte = 0;
	int idx_start_char;
	std::string val1;
	std::string val2;
	read_state_option read_stat = SCENARIO_BYTES;

	// append records (read from stdin)
	con.Query("PRAGMA force_compression='fsst'");
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

		while (idx_buf < n_read) {
			if (read_stat == SCENARIO_BYTES) {
				assert(idx_scenario_byte < NR_SCENARIO_BYTES);
				scenario_buf[idx_scenario_byte] = buf[idx_buf];
				idx_scenario_byte++;
				if (idx_scenario_byte == NR_SCENARIO_BYTES) {
					read_stat = FIRST_VAL;
					idx_start_char = idx_buf + 1;
				}
			}
			if (buf[idx_buf] == ',' && (read_stat == FIRST_VAL)) {
				val1 = val1 + std::string(reinterpret_cast<const char*>(buf + idx_start_char), idx_buf - idx_start_char);
				idx_start_char = idx_buf + 1;
				read_stat = SECOND_VAL;
			}
			if ((buf[idx_buf] == '\n') && (read_stat != SCENARIO_BYTES)) {
				if (read_stat == FIRST_VAL) {
					val1 = val1 + std::string(reinterpret_cast<const char*>(buf + idx_start_char), idx_buf - idx_start_char);
				}
				else if (read_stat == SECOND_VAL) {
					val2 = val2 + std::string(reinterpret_cast<const char*>(buf + idx_start_char), idx_buf - idx_start_char);
				}
				// add row
				// TODO: apply scenario bytes to append a preprocessed row

				appender.AppendRow(val1.c_str(), val2.c_str());
				// reset
				val1 = "";
				val2 = "";
				read_stat = SCENARIO_BYTES;
				idx_scenario_byte = 0;
				idx_start_char = idx_buf + 1;
			}
			// end of read-buffer, preserve what we have so far
			if (idx_buf == n_read - 1) {
				if (read_stat == FIRST_VAL) {
					val1 = val1 + std::string(reinterpret_cast<const char*>(buf + idx_start_char), idx_buf + 1 - idx_start_char);
				} else if (read_stat == SECOND_VAL){
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
