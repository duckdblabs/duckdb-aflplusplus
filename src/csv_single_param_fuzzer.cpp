#include "duckdb.hpp"

#include <fcntl.h>
#include <iostream>
#include <string>
#include <unistd.h>
#include <vector>

std::string GetParameterString(uint8_t scenario_id) {
	std::vector<std::string> parameter_scenarios;
	parameter_scenarios.push_back("all_varchar=true");
	parameter_scenarios.push_back("allow_quoted_nulls=false");
	parameter_scenarios.push_back("auto_detect=false");
	parameter_scenarios.push_back("auto_type_candidates = ['BIGINT', 'DATE']");
	parameter_scenarios.push_back("columns = {'col1': 'INTEGER', 'col2': 'VARCHAR'}");
	parameter_scenarios.push_back("auto_detect=false, columns = {'col1': 'INTEGER', 'col2': 'VARCHAR'}"); // combi
	parameter_scenarios.push_back("compression=gzip");
	parameter_scenarios.push_back("dateformat='%d/%m/%Y'");
	parameter_scenarios.push_back("decimal_separator=','");
	parameter_scenarios.push_back("delim='@'");
	parameter_scenarios.push_back("escape='@'");
	parameter_scenarios.push_back("filename=true");
	parameter_scenarios.push_back("force_not_null=[a]");
	parameter_scenarios.push_back("header=false");
	parameter_scenarios.push_back("hive_partitioning=true");
	parameter_scenarios.push_back("ignore_errors=true");
	parameter_scenarios.push_back("max_line_size=10");
	parameter_scenarios.push_back("names=['apple','pear','banana']");
	parameter_scenarios.push_back("new_line='\\r\\n'");
	parameter_scenarios.push_back("normalize_names=true");
	parameter_scenarios.push_back("null_padding=true");
	parameter_scenarios.push_back("nullstr=['a', 'b']");
	parameter_scenarios.push_back("parallel=false");
	parameter_scenarios.push_back("quote=@");
	parameter_scenarios.push_back("sample_size=1");
	parameter_scenarios.push_back("sep='('");
	parameter_scenarios.push_back("skip=1");
	parameter_scenarios.push_back("timestampformat='%A, %-d %B %Y - %I:%M:%S %p'");
	parameter_scenarios.push_back("types=['INTEGER','INTEGER']");
	parameter_scenarios.push_back("dtypes={'a': 'DATE'}");
	parameter_scenarios.push_back("union_by_name=true");

	return (parameter_scenarios.size() ? "," + parameter_scenarios[scenario_id % parameter_scenarios.size()] : "");
}

void FileReaderFuzzer(std::string file_read_function) {
	uint8_t buf[4096];
	uint8_t scenario_buf[1];

	// create file from stdin
	std::string filename = "temp_input_file";
	int fd = open(filename.c_str(), O_CREAT | O_WRONLY | O_TRUNC, S_IRUSR | S_IWUSR);
	if (fd < 0) {
		std::cerr << "can't create data file: " << filename << std::endl;
		exit(EXIT_FAILURE);
	}

	// read first char to determine parameter scneario
	std::string parameter_string = (read(0, (void *)scenario_buf, 1)) ? GetParameterString(scenario_buf[0]) : "";

	// create a file out of the remainder of the input
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
	// std::string query = "SELECT * FROM " + file_read_function + "('" + filename + "');";
	std::string query = "SELECT * FROM " + file_read_function + "('" + filename + "'" + parameter_string + ");";
	duckdb::unique_ptr<duckdb::MaterializedQueryResult> q_result = con.Query(query);
	std::cout << q_result->ToString() << std::endl;
}

int main() {
#ifdef DUCKDB_READ_FUNCTION
	std::string file_read_function = DUCKDB_READ_FUNCTION;
	if (file_read_function != "read_csv") {
		std::cerr << "function '" + file_read_function + "' is not supported for csv_fuzzer_single_param" << std::endl;
		exit(EXIT_FAILURE);
	}
	FileReaderFuzzer(file_read_function);
#else
	static_assert(false, "error: DUCKDB_READ_FUNCTION not defined");
#endif
	return EXIT_SUCCESS;
}
