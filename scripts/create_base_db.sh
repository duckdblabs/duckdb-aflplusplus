create_base_db () {
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
}
