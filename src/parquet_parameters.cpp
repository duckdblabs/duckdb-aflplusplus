#include <string>
#include <tuple>
#include <vector>

extern const std::vector<std::tuple<std::string, std::string>> g_all_parameters = {
    std::make_tuple("binary_as_string", "BOOLEAN"),
    std::make_tuple("filename", "BOOLEAN"),
    std::make_tuple("encryption_config", "VARCHAR"),
    std::make_tuple("file_row_number", "BOOLEAN"),
    std::make_tuple("hive_partitioning", "BOOLEAN"),
    std::make_tuple("union_by_name", "BOOLEAN")
};
