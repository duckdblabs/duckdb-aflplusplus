#include "duckdb.hpp"

#include <fcntl.h>
#include <fstream>
#include <iostream>
#include <string>
#include <sys/wait.h>
#include <unistd.h>

/*
Fuzzing the wal file.
Note: all received wal file data will be processed with the same base database file!
*/
int main() {
	uint8_t buf[4096];
#ifdef DUCKDB_AFLPLUSPLUS_DIR
	std::string duckdb_aflplusplus_dir = DUCKDB_AFLPLUSPLUS_DIR;
	std::string base_db_filepath = duckdb_aflplusplus_dir + "/build/base_db";
	std::string tmp_db_filepath = duckdb_aflplusplus_dir + "/build/tmp_db";
	std::string wal_filepath = duckdb_aflplusplus_dir + "/build/tmp_db.wal";
	std::string script_path = duckdb_aflplusplus_dir + "/scripts/fix_wal_file.py";
#else
	static_assert(false, "error: DUCKDB_AFLPLUSPLUS_DIR not defined");
#endif

	// read wal file data from stdin and save it as file
	int fd = open(wal_filepath.c_str(), O_CREAT | O_WRONLY | O_TRUNC, S_IRUSR | S_IWUSR);
	if (fd < 0) {
		std::cerr << "can't create data file: " << wal_filepath << std::endl;
		exit(EXIT_FAILURE);
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

	// run fixup script: fix_wal_file.py
	pid_t child_pid = fork();
	if (child_pid == 0) {
		// child process, -> run fixup script
		if (execl(script_path.c_str(), script_path.c_str(), wal_filepath.c_str(), (char *)(nullptr)) < 0) {
			perror(NULL);
			exit(EXIT_FAILURE);
		}
	} else {
		// wait for fixup script
		int stat_loc;
		if (waitpid(child_pid, &stat_loc, 0) < 0) {
			perror(NULL);
			exit(EXIT_FAILURE);
		}
		if (!WIFEXITED(stat_loc)) {
			std::cerr << "error in running script: " << script_path << std::endl;
			exit(EXIT_FAILURE);
		}

		// get a fresh copy of the base database:
		std::ifstream src(base_db_filepath.c_str(), std::ios::binary);
		std::ofstream dst(tmp_db_filepath.c_str(), std::ios::binary);
		dst << src.rdbuf();
		dst.close();

		// ingest database file (this will also process the .wal file) to test if it causes a crash
		duckdb::DuckDB db(tmp_db_filepath.c_str());
		duckdb::Connection con(db);
		std::string query = "ATTACH '" + tmp_db_filepath + "' AS tmp_db (READ_ONLY); use tmp_db; show tables;";
		duckdb::unique_ptr<duckdb::MaterializedQueryResult> q_result = con.Query(query);
		std::cout << q_result->ToString() << std::endl;
	}
}
