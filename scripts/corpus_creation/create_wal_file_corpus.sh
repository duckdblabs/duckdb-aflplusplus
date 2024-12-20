#!/bin/bash
source $(dirname $0)/create_base_db.sh

if [[ -z "${CORPUS_DIR}" ]]; then
  wal_corpus_dir=$(dirname $(dirname $(dirname $(realpath $0))))/corpus/walfiles
else
  wal_corpus_dir="${CORPUS_DIR}/walfiles"
fi

if [[ -z "${BUILD_DIR}" ]]; then
  build_dir=$(dirname $(dirname $(dirname $(realpath $0))))/build
else
  build_dir="${BUILD_DIR}"
fi

# delete existing corpus
rm -rf $wal_corpus_dir
mkdir -p $wal_corpus_dir

# create 'base_db' (sourced function)
create_base_db

# create wal files by doing transactions without checkpointing
for mod_file in $(dirname $0)/wal_file_corpus_init/*.sql
do
  cp base_db tmp_db
  query="PRAGMA disable_checkpoint_on_shutdown;"$(cat $mod_file)
  duckdb "tmp_db" -c "$query" > /dev/null
  mv tmp_db.wal ${wal_corpus_dir}/$(basename $mod_file '.sql').wal
done
rm -f tmp_db

# base_db is considered a build file
mkdir -p $build_dir
mv base_db ${build_dir}/base_db
