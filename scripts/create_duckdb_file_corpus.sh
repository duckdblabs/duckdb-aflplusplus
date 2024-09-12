#!/bin/bash
duckdb_corpus_dir="./corpus/duckdbfiles/"

# delete existing corpus
rm -rf $duckdb_corpus_dir
mkdir -p $duckdb_corpus_dir

# create .duckdb files
for db_init_file in ./scripts/duckdb_corpus_init/*.sql;
do
	db_name=$duckdb_corpus_dir$(basename $db_init_file '.sql').duckdb
	duckdb -init $db_init_file $db_name ";"
	# duckdb $db_name "show tables;"
done
