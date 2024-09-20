#!/usr/bin/env python3

'''
Script to naively fixup duckdb database files that have been corrupted by the mutator function of the fuzzer.
With this fixup, we bypass the initial validations of the db-file importer, for better fuzz results.
'''

import io
import os
import sys
import struct

HEADER_SIZE = 12288  # e.g. 3 headers, 4 KB each
BLOCK_SIZE = 256 * 1024  # 256 KB
DUCKDB_STORAGE_VERSION = 64  # https://duckdb.org/docs/internals/storage#storage-version-table


def fix_filesize_header_checksums(db_file_path):
    with open(db_file_path, 'r+b') as db_file:
        updated_file_size = correct_filesize(db_file_path, db_file)
        correct_headers(db_file)
        correct_block_checksums(updated_file_size, db_file)


# appends 0-bytes to match a valid duckdb filesize: HEADER_SIZE + N * BLOCK_SIZE
def correct_filesize(db_file_path, db_file):
    file_size = os.stat(db_file_path).st_size
    valid_db_file_size = HEADER_SIZE
    while file_size > valid_db_file_size:
        valid_db_file_size += BLOCK_SIZE
    if file_size < valid_db_file_size:
        db_file.seek(0, io.SEEK_END)
        db_file.write(b'\x00' * (valid_db_file_size - file_size))
    return valid_db_file_size


# sets magic bytes, DB storage version and header checksums
def correct_headers(db_file):
    # fix main header (4 KB)
    db_file.seek(8)
    db_file.write("DUCK".encode('utf-8'))
    db_file.write(struct.pack('<Q', DUCKDB_STORAGE_VERSION))
    db_file.write("FUZZ".encode('utf-8'))  # add 'FUZZ' for debug purposes
    update_checksum(db_file, 0, 4096)
    # fix table headers (two times 4 KB)
    update_checksum(db_file, 4096, 4096)
    update_checksum(db_file, 8192, 4096)


# sets checksum per block
def correct_block_checksums(file_size, db_file):
    assert (file_size - HEADER_SIZE) % BLOCK_SIZE == 0
    nr_blocks = (file_size - HEADER_SIZE) // BLOCK_SIZE
    for block_nr in range(nr_blocks):
        update_checksum(db_file, HEADER_SIZE + (block_nr * BLOCK_SIZE), BLOCK_SIZE)


# sets 8 byte checksum at pos; other bytes are read as uint64 and are input for the checksum calculation
def update_checksum(db_file, pos, byte_size):
    assert (byte_size > 8) and (byte_size % 8 == 0)
    db_file.seek(pos)
    current_checksum = int.from_bytes(db_file.read(8), "little")
    # calc checksum, based on: duckdb/src/common/checksum.cpp
    result = 5381  # magic number (prime) to initialize algorithm
    nr_long_ints = (byte_size // 8) - 1
    long_int_tup = struct.unpack(f'{str(nr_long_ints)}Q', db_file.read(nr_long_ints * 8))
    for int_val in long_int_tup:
        result = result ^ checksum_base(int_val)  # bitwise XOR
    # store result
    if result != current_checksum:
        db_file.seek(pos)
        db_file.write(struct.pack('<Q', result))


def checksum_base(x: int):
    return (x * 0xBF58476D1CE4E5B9) % (1 << 64)  # modulo operator to mimic C-style integer overflow


if __name__ == "__main__":
    try:
        db_file_path = sys.argv[1]
    except:
        sys.exit("ERROR. No DB file provided")
    fix_filesize_header_checksums(db_file_path)
