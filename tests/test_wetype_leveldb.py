import struct
import tempfile
import unittest
from pathlib import Path

from wetype_leveldb import (
    LEVELDB_MAGIC,
    WETYPE_USER_PAIR_PREFIX,
    _snappy_decompress,
    decode_wetype_pair_key,
    scan_wetype_leveldb,
)


def varint(value: int) -> bytes:
    output = bytearray()
    while value >= 0x80:
        output.append((value & 0x7F) | 0x80)
        value >>= 7
    output.append(value)
    return bytes(output)


def data_block(entries: list[tuple[bytes, bytes]]) -> bytes:
    body = bytearray()
    for key, value in entries:
        body += varint(0)
        body += varint(len(key))
        body += varint(len(value))
        body += key
        body += value
    body += struct.pack("<II", 0, 1)
    return bytes(body)


def block_with_trailer(block: bytes) -> bytes:
    return block + b"\x00" + b"\x00" * 4


def internal_key(user_key: bytes, sequence: int, value_type: int = 1) -> bytes:
    return user_key + ((sequence << 8) | value_type).to_bytes(8, "little")


def write_table(path: Path, entries: list[tuple[bytes, int, int]]) -> None:
    table_entries = [
        (internal_key(key, sequence, value_type), b"")
        for key, sequence, value_type in entries
    ]
    raw_data = data_block(table_entries)
    data_part = block_with_trailer(raw_data)
    handle = varint(0) + varint(len(raw_data))
    raw_index = data_block([(b"index", handle)])
    index_offset = len(data_part)
    index_part = block_with_trailer(raw_index)
    handles = varint(0) + varint(0) + varint(index_offset) + varint(len(raw_index))
    footer = handles + b"\x00" * (40 - len(handles)) + struct.pack("<Q", LEVELDB_MAGIC)
    path.write_bytes(data_part + index_part + footer)


def write_log(path: Path, sequence: int, entries: list[tuple[bytes, int]]) -> None:
    batch = bytearray(struct.pack("<QI", sequence, len(entries)))
    for key, value_type in entries:
        batch.append(value_type)
        batch += varint(len(key))
        batch += key
        if value_type == 1:
            batch += varint(0)
    header = struct.pack("<IHB", 0, len(batch), 1)
    path.write_bytes(header + batch)


class WeTypeLevelDBTests(unittest.TestCase):
    def test_decode_pair_key(self):
        key = WETYPE_USER_PAIR_PREFIX + b"wei,xin\x01" + "微信".encode()
        decoded = decode_wetype_pair_key(key, 7)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded.pinyin, "wei'xin")
        self.assertEqual(decoded.word, "微信")
        self.assertEqual(decoded.sequence, 7)

    def test_snappy_literal_and_copy(self):
        self.assertEqual(_snappy_decompress(b"\x05\x10hello"), b"hello")
        self.assertEqual(_snappy_decompress(b"\x08\x04ab\x16\x02\x00"), b"abababab")

    def test_scan_resolves_newer_log_tombstone(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp)
            (db / "CURRENT").write_text("MANIFEST-000001\n", encoding="ascii")
            deleted_key = WETYPE_USER_PAIR_PREFIX + "jiu,ci\x01旧词".encode()
            live_key = WETYPE_USER_PAIR_PREFIX + "xin,ci\x01新词".encode()
            malformed_key = WETYPE_USER_PAIR_PREFIX + b"bad-key"
            write_table(
                db / "000001.ldb",
                [(deleted_key, 10, 1), (live_key, 11, 1), (malformed_key, 12, 1)],
            )
            write_log(db / "000002.log", 20, [(deleted_key, 0)])

            words, stats = scan_wetype_leveldb(db)

            self.assertEqual([(item.pinyin, item.word) for item in words], [("xin'ci", "新词")])
            self.assertEqual(stats.table_files, 1)
            self.assertEqual(stats.log_files, 1)
            self.assertEqual(stats.live_pair_keys, 1)
            self.assertEqual(stats.deleted_pair_keys, 1)
            self.assertEqual(stats.malformed_pair_keys, 1)


if __name__ == "__main__":
    unittest.main()
