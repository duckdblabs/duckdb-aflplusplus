#include "duckdb.hpp"

#include <cassert>
#include <iostream>
#include <unistd.h>

const int NR_SCENARIO_BYTES = 3;
const int BUFF_SIZE = 4096;


void AppendScenarioRow(duckdb::Appender &appender, uint8_t scenario_buf[NR_SCENARIO_BYTES], std::string &val1,
					   std::string &val2) {
	// TODO: apply scenario bytes to append a preprocessed row
	appender.AppendRow(val1.c_str(), val2.c_str());
}

void AppenderFuzzer() {
	assert(BUFF_SIZE > NR_SCENARIO_BYTES);

	duckdb::DuckDB db("tempdb.duckdb");
	duckdb::Connection con(db);
	uint8_t buf[BUFF_SIZE];
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
	read_state_option read_state = SCENARIO_BYTES;

	// append records (read from stdin)
	con.Query("PRAGMA force_compression='fsst'");
	con.Query("CREATE OR REPLACE TABLE tbl (col1 VARCHAR, col2 VARCHAR)");
	duckdb::Appender appender(con, "tbl");
	while (n_read != 0) {
		// before reading new chunk, preserve partial values of previous chunck
		if (idx_buf >= idx_start_char) {
			if (read_state == FIRST_VAL) {
				val1 = val1 + std::string(reinterpret_cast<const char*>(buf + idx_start_char), idx_buf - idx_start_char);
			}
			if (read_state == SECOND_VAL) {
				val2 = val2 + std::string(reinterpret_cast<const char*>(buf + idx_start_char), idx_buf - idx_start_char);
			}
		}
		// read new chunck
		n_read = read(0, (void *)buf, BUFF_SIZE);
		if (n_read < 0) {
			std::cout << "error in read: " << n_read << std::endl;
			perror(NULL);
			exit(EXIT_FAILURE);
		}
		// parse chunck: split rows by newline, split values by first comma (if any)
		idx_buf = 0;
		idx_start_char = 0;
		while (idx_buf < n_read) {
			if (read_state == SCENARIO_BYTES) {
				assert(idx_scenario_byte < NR_SCENARIO_BYTES);
				scenario_buf[idx_scenario_byte] = buf[idx_buf];
				idx_scenario_byte++;
				if (idx_scenario_byte == NR_SCENARIO_BYTES) {
					// reset
					idx_scenario_byte = 0;
					read_state = FIRST_VAL;
					idx_start_char = idx_buf + 1;
				}
			} else if (buf[idx_buf] == '\n') {
				if (read_state == FIRST_VAL) {
					val1 = val1 + std::string(reinterpret_cast<const char*>(buf + idx_start_char), idx_buf - idx_start_char);
				}
				if (read_state == SECOND_VAL) {
					val2 = val2 + std::string(reinterpret_cast<const char*>(buf + idx_start_char), idx_buf - idx_start_char);
				}
				AppendScenarioRow(appender, scenario_buf, val1, val2);
				// reset
				val1 = "";
				val2 = "";
				read_state = SCENARIO_BYTES;
				idx_start_char = idx_buf + 1;
			} else if (buf[idx_buf] == ',' && read_state == FIRST_VAL) {
				assert(idx_buf >= idx_start_char);
				val1 = val1 + std::string(reinterpret_cast<const char*>(buf + idx_start_char), idx_buf - idx_start_char);
				idx_start_char = idx_buf + 1;
				read_state = SECOND_VAL;
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
	con.Query("checkpoint");

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
