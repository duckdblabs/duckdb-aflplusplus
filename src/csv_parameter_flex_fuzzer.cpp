// in contrast to the 'csv_parameter_fuzzer', this fuzzer can call
// read_csv() with multiple parameters.

#include "duckdb.hpp"

#include <exception>
#include <fcntl.h>
#include <iostream>
#include <string>
#include <unistd.h>

#define MAX_ARGUMENT_LENGTH 255

// NOTE: keep this list in sync with 'create_prepended_csv_corpus.py' !!
const std::vector<std::tuple<std::string, std::string>> g_all_parameters = {
    std::make_tuple("all_varchar", "BOOLEAN"),
    std::make_tuple("allow_quoted_nulls", "BOOLEAN"),
    std::make_tuple("auto_detect", "BOOLEAN"),
    std::make_tuple("auto_type_candidates", "VARCHAR"),
    std::make_tuple("columns", "VARCHAR"),
    std::make_tuple("compression", "VARCHAR"),
    std::make_tuple("dateformat", "VARCHAR"),
    std::make_tuple("decimal_separator", "VARCHAR"),
    std::make_tuple("delim", "VARCHAR"),
    std::make_tuple("delimiter", "VARCHAR"),
    std::make_tuple("dtypes", "VARCHAR"),
    std::make_tuple("escape", "VARCHAR"),
    std::make_tuple("filename", "BOOLEAN"),
    std::make_tuple("force_not_null", "VARCHAR"),
    std::make_tuple("header", "BOOLEAN"),
    std::make_tuple("hive_partitioning", "BOOLEAN"),
    std::make_tuple("ignore_errors", "BOOLEAN"),
    std::make_tuple("max_line_size", "INTEGER"),
    std::make_tuple("names", "VARCHAR"),
    std::make_tuple("new_line", "VARCHAR"),
    std::make_tuple("normalize_names", "BOOLEAN"),
    std::make_tuple("null_padding", "BOOLEAN"),
    std::make_tuple("nullstr", "VARCHAR"),
    std::make_tuple("parallel", "BOOLEAN"),
    std::make_tuple("quote", "VARCHAR"),
    std::make_tuple("sample_size", "INTEGER"),
    std::make_tuple("sep", "VARCHAR"),
    std::make_tuple("skip", "INTEGER"),
    std::make_tuple("timestampformat", "VARCHAR"),
    std::make_tuple("types", "VARCHAR"),
    std::make_tuple("union_by_name", "BOOLEAN"),

    // undocumented
    std::make_tuple("buffer_size", "INTEGER"),
    std::make_tuple("column_names", "VARCHAR"),
    std::make_tuple("column_types", "VARCHAR"),
    std::make_tuple("comment", "VARCHAR"),
    std::make_tuple("date_format", "VARCHAR"),
    std::make_tuple("encoding", "VARCHAR"),
    std::make_tuple("force_quote", "VARCHAR"),
    std::make_tuple("hive_type", "VARCHAR"),
    std::make_tuple("hive_type_autocast", "BOOLEAN"),
    std::make_tuple("hive_types", "VARCHAR"),
    std::make_tuple("hive_types_autocast", "BOOLEAN"),
    std::make_tuple("maximum_line_size", "INTEGER"),
    std::make_tuple("null", "VARCHAR"),
    std::make_tuple("prefix", "VARCHAR"),
    std::make_tuple("rejects_limit", "INTEGER"),
    std::make_tuple("rejects_scan", "VARCHAR"),
    std::make_tuple("rejects_table", "VARCHAR"),
    std::make_tuple("rfc_4180", "BOOLEAN"),
    std::make_tuple("store_rejects", "BOOLEAN"),
    std::make_tuple("suffix", "VARCHAR"),
    std::make_tuple("timestamp_format", "VARCHAR"),
};

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
					}
					else {
						argument_str = "42";
					}
				} else if (parameter_type == "BOOLEAN") {
					if (read_len >= 1) {
						argument_str = (argument_buf[0] % 2) ? "true" : "false";
					}
					else {
						argument_str = "true";
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
	if (file_read_function != "read_csv") {
		std::cerr << "function '" + file_read_function + "' is not supported for csv_parameter_flex_fuzzer"
		          << std::endl;
		exit(EXIT_FAILURE);
	}
	FileReaderFuzzer(file_read_function);
#else
	static_assert(false, "error: DUCKDB_READ_FUNCTION not defined");
#endif
	return EXIT_SUCCESS;
}
