#include "duckdb.hpp"

#include <cassert>
#include <iostream>
#include <iomanip>
#include <unistd.h>
#include <cstdio>
#include <sstream>

const int NR_SCENARIO_BYTES = 3;
const int BUFF_SIZE = 4096;

std::string CreatePrintableString(const std::string &str) {
	std::string printable_str;
	printable_str.reserve(str.size());
	for (unsigned char ch : str) {
		if (std::isprint(ch)) {
			printable_str.push_back(ch);
		} else {
			// convert non-printable chars into ASCII range 32..126 (95 characters)
			unsigned char printable = (ch % 95) + 32;
			printable_str.push_back(printable);
		}
	}
	return printable_str;
}

std::string generate_random_string(uint16_t len, const std::string &seed_str) {
	const std::string charset =
		"0123456789"
		"ABCDEFGHIJKLMNOPQRSTUVWXYZ"
		"abcdefghijklmnopqrstuvwxyz";
	unsigned int seed = std::hash<std::string>{}(seed_str);
	std::mt19937 num_generator(seed);
	std::uniform_int_distribution<> dist(0, charset.size() - 1);

	std::string str;
	str.reserve(len);
	for (uint16_t i = 0; i < len; ++i) {
		str += charset[dist(num_generator)];
	}
	return str;
}

// creates a 3-char hex-string
std::string intToHexStr(uint16_t value) {
	std::stringstream ss;
	ss << std::hex << std::setw(3) << std::setfill('-') << (value % 4096);
	return ss.str();
}

void RepeatString(std::string &str, uint16_t nr_repeats, bool apply_rotating_suffix) {
	assert(nr_repeats > 1);
	const std::string initial_str(str);
	const size_t initial_str_len = initial_str.size();
	assert(initial_str_len > 0);
	const uint8_t suffix_size = apply_rotating_suffix ? 3 : 0;

	// create string
	str.resize((initial_str_len + suffix_size) * nr_repeats);
	for (uint16_t rep_nr = 0; rep_nr < nr_repeats; rep_nr++) {
		idx_t idx_rep_start = rep_nr * (initial_str_len + suffix_size);
		if (rep_nr > 0) {
			// append string (first one is already in place)
			for (idx_t idx_ch = 0; idx_ch < initial_str_len; idx_ch++) {
				str[idx_rep_start + idx_ch] = initial_str[idx_ch];
			}
		}
		if (apply_rotating_suffix) {
			// append 3 char suffix
			std::string suffix = intToHexStr(rep_nr);
			for (size_t idx_suffix = 0; idx_suffix < 3; idx_suffix++) {
				str[idx_rep_start + initial_str_len + idx_suffix] = suffix[idx_suffix];
			}
		}
	}
}

std::string CreateStringWithSuffix(const std::string &str, uint16_t num) {
	std::string str_out = std::string(str);
	str_out.resize(str.size() + 3);
	std::string suffix = intToHexStr(num);
	std::copy(suffix.begin(), suffix.end(), str_out.end() - 3);
	return str_out;
}

void GetBoolSettings(uint8_t &scenario_byte, bool (&bool_settings)[8]) {
	for (int i = 0; i < 8; i++) {
		bool_settings[i] = (scenario_byte >> i) & 0b00000001;
	}
}

void AppendScenarioRow(duckdb::Appender &appender, uint8_t scenario_buf[NR_SCENARIO_BYTES], std::string &val1,
					   std::string &val2) {
	// use first scenario byte to get bool-settings
	bool bool_settings[8];
	GetBoolSettings(scenario_buf[0], bool_settings);

	// use second and third scenario byte to get n value [0 - 400]
	assert(NR_SCENARIO_BYTES == 3);
	uint16_t n_value = ((static_cast<uint16_t>(scenario_buf[1]) << 8) | static_cast<uint16_t>(scenario_buf[2])) % 4010;

	// apply bool-settings
	// 0 - replace val1 by ""
	std::string append_str1 = (bool_settings[0]) ? "" : val1;

	// 1 - replace val2 by random (non-compressible) string (deterministic, of lenght n)
	std::string append_str2 = (bool_settings[1]) ? generate_random_string(n_value, val2) : val2;

	// 2 - replace val1: convert to printable chars
	if (bool_settings[2] && append_str1 != "") {
		append_str1 = CreatePrintableString(append_str1);
	}

	// 3 - use rotating suffixes in repetitions
	bool apply_rotating_suffix = (bool_settings[3]) ? true : false;

	// 4 - repeat val1 n times
	if (bool_settings[4] && append_str1 != "" && n_value >= 2) {
		RepeatString(append_str1, n_value, apply_rotating_suffix);
	}

	// 5 - repeat val2 n times
	if (bool_settings[5] && append_str2 != "" && n_value >= 2) {
		RepeatString(append_str2, n_value, apply_rotating_suffix);
	}

	// 6 - append same row n times
	uint16_t nr_row_inserts = (bool_settings[6]) ? n_value : 1;

	// 7 - replace empty strings by NULL
	if (bool_settings[7]) {
		duckdb::Value append_val_1 = (append_str1 == "") ? duckdb::Value(nullptr) : duckdb::Value(append_str1);
		duckdb::Value append_val_2 = (append_str2 == "") ? duckdb::Value(nullptr) : duckdb::Value(append_str2);
		for (u_int16_t i = 0; i < nr_row_inserts; i++) {
			appender.AppendRow(append_val_1, append_val_2);
			// debug
			// std::cout << "val append: " << append_val_1.ToString() << ", " << append_val_1.ToString() << std::endl;
		}
	} else {
		for (u_int16_t i = 0; i < nr_row_inserts; i++) {
			appender.AppendRow(duckdb::string_t(append_str1), duckdb::string_t(append_str2));
			// std::cout << "str append: " << append_str1 << ", " << append_str2 << std::endl;
		}
	}

	// DEBUG: print bool settings:
	// std::cout << "scenario_buf[0]: " << static_cast<unsigned int>(scenario_buf[0]) << ": ";
	// for (bool b : bool_settings) {
	// 	std::cout << b;
	// }
	// std::cout << std::endl;
	// std::cout << "-----------" << std::endl;
}

void AppenderFuzzer() {
	// create duckdb db
	duckdb::DBConfig config;
	config.SetOptionByName("default_block_size", duckdb::Value(16384));
	duckdb::DuckDB db("tempdb.duckdb", &config);
	duckdb::Connection con(db);

	// append data (read from stdin)
	assert(BUFF_SIZE > NR_SCENARIO_BYTES);
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

	con.Query("PRAGMA force_compression='fsst'");
	con.Query("CREATE OR REPLACE TABLE tbl (col1 VARCHAR, col2 VARCHAR)");
	duckdb::Appender appender(con, "tbl");
	while (n_read != 0) {
		// before reading new chunk, preserve partial values of previous chunck
		if (idx_buf >= idx_start_char) {
			if (read_state == FIRST_VAL) {
				val1 += std::string(reinterpret_cast<const char*>(buf + idx_start_char), idx_buf - idx_start_char);
			}
			if (read_state == SECOND_VAL) {
				val2 += std::string(reinterpret_cast<const char*>(buf + idx_start_char), idx_buf - idx_start_char);
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
					val1 += std::string(reinterpret_cast<const char*>(buf + idx_start_char), idx_buf - idx_start_char);
				}
				if (read_state == SECOND_VAL) {
					val2 += std::string(reinterpret_cast<const char*>(buf + idx_start_char), idx_buf - idx_start_char);
				}
				AppendScenarioRow(appender, scenario_buf, val1, val2);
				// reset
				val1 = "";
				val2 = "";
				read_state = SCENARIO_BYTES;
				idx_start_char = idx_buf + 1;
			} else if (buf[idx_buf] == ',' && read_state == FIRST_VAL) {
				assert(idx_buf >= idx_start_char);
				val1 += std::string(reinterpret_cast<const char*>(buf + idx_start_char), idx_buf - idx_start_char);
				idx_start_char = idx_buf + 1;
				read_state = SECOND_VAL;
			}
			idx_buf++;
		}
	}
	// add final row
	if (read_state != SCENARIO_BYTES) {
		AppendScenarioRow(appender, scenario_buf, val1, val2);
	}
	// flush
	appender.Close();
	con.Query("checkpoint");

	// force decompression
	duckdb::unique_ptr<duckdb::QueryResult> result;
	result = con.Query("FROM tbl");
	result->ToString();

	// debug
	// std::cout << result->ToString() << std::endl;
	// std::cout << con.Query("SELECT count(*) FROM tbl")->ToString() << std::endl;
}

int main() {
	try {
		AppenderFuzzer();
	} catch (duckdb::InvalidInputException &e) {
		std::cout << e.what() << std::endl;
	}
	// cleanup
	std::remove("tempdb.duckdb");
	std::remove("tempdb.duckdb.wal");
}
