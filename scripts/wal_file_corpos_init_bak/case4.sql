SET checkpoint_threshold = '1.0 GiB';
PRAGMA disable_checkpoint_on_shutdown;
CREATE TABLE myNewTable (myCol integer);
INSERT INTO myNewTable VALUES (42);
INSERT INTO myNewTable VALUES (43);
