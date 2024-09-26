#!/usr/bin/env python3
import io
import os
import struct
import sys
from typing import BinaryIO


def fix_wal_file(wal_file_path: str):
    if not os.path.isfile(wal_file_path):
        sys.exit(f"ERROR. wal file not found: '{wal_file_path}'")
    file_size = os.stat(wal_file_path).st_size
    with open(wal_file_path, 'r+b') as wal_file:
        correct_file_header(wal_file)
        correct_entry(wal_file, file_size)


def correct_file_header(wal_file: BinaryIO):
    # wal file header contains 8 fixed bytes, see WriteAheadLog::WriteVersion():
    #   '\x64\x00' -> 100, "wal_type"
    #   '\x62'     -> 98   WAL_VERSION
    #   '\x65\x00' -> 101, "version"
    #   '\x02'     -> 02   WAL_VERSION_NUMBER
    #   '\xff\xff' -> end of header block
    expected_header = b'\x64\x00\x62\x65\x00\x02\xff\xff'
    wal_file.seek(0)
    current_header = wal_file.read(8)
    if current_header != expected_header:
        wal_file.seek(0)
        wal_file.write(expected_header)

# every entry has uint64 size, and uint64 checksum, followed by the wal entry itself
def correct_entry(wal_file: BinaryIO, file_size: int):
    entry_start_pos = 8  # first entry starts after 8-byte file header
    while entry_start_pos < file_size:
        # print(f"processing entry at pos: {entry_start_pos}")
        entry_data_size = validate_and_correct_entry_size(entry_start_pos, file_size, wal_file)
        validate_and_correct_checksum(entry_start_pos, entry_data_size, wal_file)
        entry_start_pos += entry_data_size + 16  # every entry has uint64 size, and uint64 checksum


def validate_and_correct_entry_size(entry_start_pos: int, file_size: int, wal_file: BinaryIO) -> int:
    wal_file.seek(entry_start_pos)
    entry_data_size = int.from_bytes(wal_file.read(8), "little")
    entry_size = entry_data_size + 16  # every entry has uint64 size, and uint64 checksum
    if entry_start_pos + entry_size > file_size:
        if entry_data_size > 40000:
            # actual file size not congruent with size value in file; fix by changing size value in file
            wal_file.seek(entry_start_pos)
            entry_data_size = file_size - entry_start_pos - 16
            wal_file.write(struct.pack('<Q', entry_data_size))
            # print(f"updated size at pos '{entry_start_pos}' to {entry_data_size} ('{entry_data_size.to_bytes(8, 'little').hex()}')")
        else:
            # actual file size not congruent with size value in file; fix by appending 0-bytes
            wal_file.seek(0, io.SEEK_END)
            wal_file.write(b'\x00' * (entry_start_pos + entry_size - file_size))
            # print(f"appended size, added {(entry_start_pos + entry_size - file_size)} zero-bytes at the end of the file")
            wal_file.seek(entry_start_pos + 8)
    return entry_data_size


# assumes cursor is at the beginning of the checksum
def validate_and_correct_checksum(entry_start_pos: int, entry_data_size: int, wal_file: BinaryIO):
    current_checksum = int.from_bytes(wal_file.read(8), "little")
    entry_content: bytes = wal_file.read(entry_data_size)
    calculated_checksum = calc_checksum(entry_content, entry_data_size)
    if calculated_checksum != current_checksum:
        wal_file.seek(entry_start_pos + 8)
        wal_file.write(struct.pack('<Q', calculated_checksum))
        # print(f"updated checksum at pos '{entry_start_pos + 8}' to '{calculated_checksum.to_bytes(8, 'little').hex()}'")


# calc checksum, based on: duckdb/src/common/checksum.cpp
def calc_checksum(entry_data: bytes, entry_data_size: int) -> int:
    tail_length = entry_data_size % 8
    if tail_length == 0:
        checksum = calc_checksum_multiples_of_8(entry_data, entry_data_size)
    else:
        nr_long_ints = entry_data_size // 8
        main_chunk = entry_data[: nr_long_ints * 8]
        tail_chunk = entry_data[nr_long_ints * 8 :]
        checksum_base = calc_checksum_multiples_of_8(main_chunk, nr_long_ints * 8)
        tail_hash = calc_tail_hash(tail_chunk, entry_data_size % 8)
        checksum = checksum_base ^ tail_hash
    return checksum


def calc_checksum_multiples_of_8(byte_data: bytes, data_size: int) -> int:
    assert data_size % 8 == 0
    result = 5381  # magic number (prime) to initialize algorithm
    nr_long_ints = data_size // 8
    if nr_long_ints > 0:
        long_int_tup = struct.unpack(f'{str(nr_long_ints)}Q', byte_data)
        for int_val in long_int_tup:
            result = result ^ checksum_base(int_val)  # bitwise XOR
    return result


# adjusted from duckdb/src/common/types/hash.cpp
# MIT License
# Copyright (c) 2018-2021 Martin Ankerl
# https://github.com/martinus/robin-hood-hashing/blob/3.11.5/LICENSE
def calc_tail_hash(tail_data: bytes, tail_size: int) -> int:
    assert tail_size < 8
    M = 0xC6A4A7935BD1E995
    SEED = 0xE17A1465
    R = 47
    h = SEED ^ ((tail_size * M) % (1 << 64))
    if tail_size == 7:
        h ^= tail_data[6] << 48
    if tail_size >= 6:
        h ^= tail_data[5] << 40
    if tail_size >= 5:
        h ^= tail_data[4] << 32
    if tail_size >= 4:
        h ^= tail_data[3] << 24
    if tail_size >= 3:
        h ^= tail_data[2] << 16
    if tail_size >= 2:
        h ^= tail_data[1] << 8
    if tail_size >= 1:
        h ^= tail_data[0]
        h = (h * M) % (1 << 64)
    h ^= h >> R
    h = (h * M) % (1 << 64)
    h ^= h >> R
    return h


def checksum_base(x: int) -> int:
    return (x * 0xBF58476D1CE4E5B9) % (1 << 64)  # modulo operator to mimic C-style integer overflow


if __name__ == "__main__":
    try:
        wal_file_path = sys.argv[1]
    except:
        sys.exit("ERROR. No Wal file provided")
    fix_wal_file(wal_file_path)
