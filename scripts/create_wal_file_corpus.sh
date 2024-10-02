#!/bin/bash
if [[ -z "${CORPUS_DIR}" ]]; then
  wal_corpus_dir=$(dirname $(dirname $(realpath $0)))/corpus/walfiles
else
  wal_corpus_dir="${CORPUS_DIR}/walfiles"
fi

if [[ -z "${BUILD_DIR}" ]]; then
  build_dir=$(dirname $(dirname $(realpath $0)))/build
else
  build_dir="${BUILD_DIR}"
fi

# delete existing corpus
rm -rf $wal_corpus_dir
mkdir -p $wal_corpus_dir

# create base db
rm -f base_db
q_init="
CREATE SCHEMA s0;
CREATE TABLE t0 (c0 integer, d0 integer);
CREATE TABLE s0.t0 (c0 integer, d0 integer);
INSERT INTO t0 VALUES (42, 1);
CREATE VIEW v0 AS SELECT * FROM t0;
CREATE INDEX i0 ON t0 (c0);
CREATE SEQUENCE se0;
CREATE TYPE ty0 AS STRUCT(i INTEGER);
CREATE MACRO m0(a, b) AS a + b;
CREATE MACRO mt0() AS TABLE SELECT '' AS c0;
CHECKPOINT;
"
duckdb base_db -c "$q_init" > /dev/null

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
