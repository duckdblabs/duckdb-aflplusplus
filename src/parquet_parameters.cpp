#include <string>
#include <tuple>
#include <vector>

extern const std::vector<std::tuple<std::string, std::string>> g_all_parameters = {
    std::make_tuple("binary_as_string", "BOOLEAN"),
    std::make_tuple("bloom_filter_false_positive_ratio", "DOUBLE"),
    std::make_tuple("can_have_nan", "BOOLEAN"),
    std::make_tuple("chunk_size", "INTEGER"),
    std::make_tuple("codec", "VARCHAR"),
    std::make_tuple("compression_level", "INTEGER"),
    std::make_tuple("debug_use_openssl", "BOOLEAN"),
    std::make_tuple("dictionary_compression_ratio_threshold", "VARCHAR"),
    std::make_tuple("dictionary_size_limit", "INTEGER"),
    std::make_tuple("encryption_config", "VARCHAR"),
    std::make_tuple("explicit_cardinality", "INTEGER"),
    std::make_tuple("field_ids", "VARCHAR"),
    std::make_tuple("file_row_number", "BOOLEAN"),
    std::make_tuple("filename", "VARCHAR"),
    std::make_tuple("geoparquet_version", "VARCHAR"),
    std::make_tuple("hive_partitioning", "BOOLEAN"),
    std::make_tuple("kv_metadata", "VARCHAR"),
    std::make_tuple("parquet_version", "VARCHAR") ,
    std::make_tuple("row_group_size_bytes", "VARCHAR"),
    std::make_tuple("row_group_size", "INTEGER"),
    std::make_tuple("row_groups_per_file", "INTEGER"),
    std::make_tuple("schema", "VARCHAR"),
    std::make_tuple("shredding", "VARCHAR"),
    std::make_tuple("string_dictionary_page_size_limit", "INTEGER"),
    std::make_tuple("union_by_name", "BOOLEAN"),
    std::make_tuple("write_bloom_filter", "BOOLEAN")
};
