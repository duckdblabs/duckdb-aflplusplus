#include "duckdb.hpp"

#include <iostream>
#include <string>
#include <unistd.h>

void fuzz_filereaders(std::string filereadFunction)
{
    if (filereadFunction != "read_csv" && filereadFunction != "read_json" && filereadFunction != "read_parquet")
    {
        std::cerr << "function '" + filereadFunction + "' is not supported" << std::endl;
        exit(1);
    }

    /*
    Move data from stdin to pipe, so duckdb can read from it.
    This is needed because duckdb checks the fd for S_ISFIFO.
    example:
      $ cat flights.csv | duckdb -c "SELECT * FROM read_csv('/dev/stdin')"
    */
    uint8_t buf[4096];
    int dataPipe[2];
    if (pipe(dataPipe) < 0)
    {
        perror(NULL);
        exit(1);
    }
    int nRead = 1;
    while (nRead != 0)
    {
        nRead = read(STDIN_FILENO, (void *)buf, 4096);
        if (nRead < 0)
        {
            perror(NULL);
            exit(1);
        }
        if (write(dataPipe[1], (void *)buf, nRead) < 0)
        {
            perror(NULL);
            exit(1);
        }
    }
    if (close(dataPipe[1]) < 0)
    {
        perror(NULL);
        exit(1);
    }

    // ingest data (to test if it crashes duckdb)
    if (dup2(dataPipe[0], STDIN_FILENO) < 0)
    {
        perror(NULL);
        exit(1);
    }
    duckdb::DuckDB db(nullptr);
    duckdb::Connection con(db);
    std::string query = "SELECT * FROM " + filereadFunction + "('/dev/stdin');";
    duckdb::unique_ptr<duckdb::MaterializedQueryResult> q_result = con.Query(query);
    q_result->ToString();
    if (close(dataPipe[0]) < 0)
    {
        perror(NULL);
        exit(1);
    }
}
