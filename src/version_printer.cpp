/*
 * This file is just to test the duckdb library as compiled by the AFL++ compiler.
 */

#include "duckdb.hpp"

#include <iostream>
#include <string>

int main() {
	duckdb::DuckDB db(nullptr);
	duckdb::Connection con(db);
	std::string query = "PRAGMA VERSION;";
    duckdb::unique_ptr<duckdb::MaterializedQueryResult> q_result = con.Query(query);
	std::cout << q_result->ToString() << std::endl;
}
