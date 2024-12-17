# include <vector>
# include <string>

extern const std::vector<std::tuple<std::string, std::string>> g_all_parameters = {
    std::make_tuple("auto_detect", "BOOLEAN"),
    std::make_tuple("columns", "VARCHAR"),
    std::make_tuple("compression", "VARCHAR"),
    std::make_tuple("convert_strings_to_integers", "BOOLEAN"),
    std::make_tuple("date_format", "VARCHAR"),
    std::make_tuple("dateform", "VARCHAR"),
    std::make_tuple("dateformat", "VARCHAR"),
    std::make_tuple("field_appearance_threshold", "DOUBLE"),
    std::make_tuple("filename", "VARCHAR"),
    std::make_tuple("format", "VARCHAR"),
    std::make_tuple("hive_partitioning", "BOOLEAN"),
    std::make_tuple("hive_type", "VARCHAR"),
    std::make_tuple("hive_type_autocast", "BOOLEAN"),
    std::make_tuple("hive_types", "VARCHAR"),
    std::make_tuple("hive_types_autocast", "BOOLEAN"),
    std::make_tuple("ignore_errors", "BOOLEAN"),
    std::make_tuple("map_inference_threshold", "INTEGER"),
    std::make_tuple("maximum_depth", "INTEGER"),
    std::make_tuple("maximum_object_size", "INTEGER"),
    std::make_tuple("maximum_sample_files", "INTEGER"),
    std::make_tuple("records", "VARCHAR"),
    std::make_tuple("sample_size", "INTEGER"),
    std::make_tuple("timestamp_format", "VARCHAR"),
    std::make_tuple("timestampform", "VARCHAR"),
    std::make_tuple("timestampformat", "VARCHAR"),
    std::make_tuple("union_by_name", "BOOLEAN")
};
