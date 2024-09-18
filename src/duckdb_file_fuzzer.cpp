#include "duckdb.hpp"

#include <fcntl.h>
#include <iostream>
#include <string>
#include <sys/wait.h>
#include <unistd.h>

int main() {
	uint8_t buf[4096];

	// create file from stdin
	std::string db_filename = "temp_input_file";
	int fd = open(db_filename.c_str(), O_CREAT | O_WRONLY | O_TRUNC, S_IRUSR | S_IWUSR);
	if (fd < 0) {
		std::cerr << "can't create data file: " << db_filename << std::endl;
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

	// run fixup script: fix_filesize_header_checksums.py
	pid_t child_pid = fork();
	std::string script_path = "/scripts/fix_filesize_header_checksums.py";
	if (child_pid == 0) {
		// child process, -> run fixup script
		if (execl(script_path.c_str(), script_path.c_str(), db_filename.c_str(), (char *)(nullptr)) < 0) {
			perror(NULL);
			exit(1);
		}
	} else {
		// wait for fixup script
		int stat_loc;
		if (waitpid(child_pid, &stat_loc, 0) < 0) {
			perror(NULL);
			exit(1);
		}
		if (!WIFEXITED(stat_loc)) {
			std::cerr << "error in running script: " << script_path << std::endl;
			exit(1);
		}

		// ingest file (to test if it crashes duckdb)
		duckdb::DuckDB db(nullptr);
		duckdb::Connection con(db);
		std::string query = "ATTACH '" + db_filename + "' AS tmp_db (READ_ONLY); use tmp_db; show tables;";
		duckdb::unique_ptr<duckdb::MaterializedQueryResult> q_result = con.Query(query);
		std::cout << q_result->ToString() << std::endl;
	}
}
