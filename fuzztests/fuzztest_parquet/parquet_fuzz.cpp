#include "duckdb.hpp"
#include <fcntl.h>
#include <iostream>
#include <unistd.h>

int main()
{
    uint8_t buf[4096];

    // create parquet file from stdin
    std::string filename = "temp_parquet_input.parquet";
    int fd = open(filename.c_str(), O_CREAT | O_WRONLY | O_TRUNC, S_IRUSR | S_IWUSR);
    if (fd < 0) {
        std::cerr << "can't create parquet file: " << filename << std::endl;
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

    // ingest parquet file (to test if it crashes duckdb)
    duckdb::DuckDB db(nullptr);
    duckdb::Connection con(db);
    std::string query = "SELECT * FROM read_parquet('" + filename + "');";
    duckdb::unique_ptr<duckdb::MaterializedQueryResult> q_result = con.Query(query);
    return 0;
}
