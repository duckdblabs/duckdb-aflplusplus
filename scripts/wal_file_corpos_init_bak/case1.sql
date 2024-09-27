SET checkpoint_threshold = '1.0 GiB';
PRAGMA disable_checkpoint_on_shutdown;
CREATE TABLE t1 (c1 integer);
CHECKPOINT;
DROP TABLE t1;
