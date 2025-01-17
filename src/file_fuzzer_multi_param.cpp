// fuzzer to call file readers read_csv(), read_json() and read_parquet() with multiple parameters.

#include "duckdb.hpp"

#include <exception>
#include <fcntl.h>
#include <iostream>
#include <string>
#include <unistd.h>

#define MAX_ARGUMENT_LENGTH 255

extern const std::vector<std::tuple<std::string, std::string>> g_all_parameters;

void FileReaderFuzzer(std::string file_read_function) {
	uint8_t file_buf[4096];
	char argument_buf[MAX_ARGUMENT_LENGTH + 1];

	std::string filename = "temp_input_file";
	int fd = open(filename.c_str(), O_CREAT | O_WRONLY | O_TRUNC, S_IRUSR | S_IWUSR);
	if (fd < 0) {
		std::cerr << "can't create data file: " << filename << std::endl;
		exit(EXIT_FAILURE);
	}

	u_int8_t nr_parameters;
	u_int8_t parameter_idx;
	u_int8_t argument_length;
	std::string total_parameter_string = "";
	std::string parameter_string = "";
	if (read(0, (void *)(&nr_parameters), 1)) {
		for (u_int8_t i_param = 0; i_param < nr_parameters; i_param++) {
			if (read(0, (void *)(&parameter_idx), 1) && read(0, (void *)(&argument_length), 1)) {
				// take modulo to prevent invalid parameter_idx numbers
				parameter_idx = parameter_idx % g_all_parameters.size();
				std::string parameter_name = std::get<0>(g_all_parameters[parameter_idx]);
				std::string parameter_type = std::get<1>(g_all_parameters[parameter_idx]);

				ssize_t read_len = read(0, (void *)argument_buf, argument_length);
				argument_buf[read_len] = '\0';
				std::string argument_str;
				int64_t argument_num;
				if (parameter_type == "VARCHAR") {
					argument_str = std::string(argument_buf);
				} else if (parameter_type == "INTEGER") {
					if (read_len == argument_length && read_len >= sizeof(int64_t)) {
						argument_num = *reinterpret_cast<int64_t *>(argument_buf);
						argument_str = std::to_string(argument_num);
					} else {
						argument_str = "42";
					}
				} else if (parameter_type == "BOOLEAN") {
					if (read_len >= 1) {
						argument_str = (argument_buf[0] % 2) ? "true" : "false";
					} else {
						argument_str = "true";
					}
				} else if (parameter_type == "DOUBLE") {
					if (read_len == argument_length && read_len >= sizeof(double)) {
						argument_num = *reinterpret_cast<double *>(argument_buf);
						argument_str = std::to_string(argument_num);
					} else {
						argument_str = "0.1";
					}
				} else {
					throw std::logic_error("parameter type not supported");
				}
				parameter_string = parameter_name + "=" + argument_str;
				total_parameter_string = total_parameter_string + ", " + parameter_string;
			}
		}
	}

	// create a file out of the remainder of the input
	ssize_t n;
	while (true) {
		n = read(0, (void *)file_buf, 4096);
		write(fd, (void *)file_buf, n);
		if (n == 0) {
			break;
		}
	}
	close(fd);

	// ingest file (to test if it crashes duckdb)
	duckdb::DuckDB db(nullptr);
	duckdb::Connection con(db);
	std::string query = "SELECT * FROM " + file_read_function + "('" + filename + "'" + total_parameter_string + ");";
	duckdb::unique_ptr<duckdb::MaterializedQueryResult> q_result = con.Query(query);
	// std::cout << q_result->ToString() << std::endl;
}

int main() {
#ifdef DUCKDB_READ_FUNCTION
	std::string file_read_function = DUCKDB_READ_FUNCTION;
	if (file_read_function != "read_csv" && file_read_function != "read_json" && file_read_function != "read_parquet") {
		std::cerr << "function '" + file_read_function + "' is not supported for parameter_flex_fuzzer" << std::endl;
		exit(EXIT_FAILURE);
	}
	FileReaderFuzzer(file_read_function);
#else
	static_assert(false, "error: DUCKDB_READ_FUNCTION not defined");
#endif
	return EXIT_SUCCESS;
}
