SET checkpoint_threshold = '1.0 GiB';
PRAGMA disable_checkpoint_on_shutdown;
CREATE TABLE myNewTable (myColumn1 integer);
