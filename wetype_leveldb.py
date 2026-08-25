"""Read WeType (微信输入法) user words from a copied LevelDB database.

This module deliberately implements only the read side of the LevelDB formats
that WeType currently writes: table files and write-ahead logs.  It never opens
the source database through LevelDB, so it cannot acquire its lock, recover it,
or mutate it.  Callers should still make a consistent snapshot before reading.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


LEVELDB_MAGIC = 0xDB4775248B80FB57
BLOCK_TRAILER_SIZE = 5
FOOTER_SIZE = 48
LOG_BLOCK_SIZE = 32768

# Current WeType 2.x user-dictionary-v2 pair key.  The key is:
#   !u_d_v_p!<comma-separated pinyin>\x01<UTF-8 word>
WETYPE_USER_PAIR_PREFIX = b"!u_d_v_p!"


class LevelDBFormatError(ValueError):
    """Raised when a LevelDB file is malformed or unsupported."""


@dataclass(frozen=True)
class WeTypeWord:
    pinyin: str
    word: str
    sequence: int


@dataclass(frozen=True)
class ScanStats:
    table_files: int
    log_files: int
    physical_records: int
    live_pair_keys: int
    deleted_pair_keys: int
    malformed_pair_keys: int


def _read_varint(data: bytes, pos: int, limit: int | None = None) -> tuple[int, int]:
    end = len(data) if limit is None else min(limit, len(data))
    value = 0
    shift = 0
    while pos < end and shift <= 63:
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, pos
        shift += 7
    raise LevelDBFormatError("truncated or oversized varint")


def _read_length_prefixed(data: bytes, pos: int) -> tuple[bytes, int]:
    size, pos = _read_varint(data, pos)
    end = pos + size
    if end > len(data):
        raise LevelDBFormatError("truncated length-prefixed value")
    return data[pos:end], end


def _snappy_decompress(data: bytes) -> bytes:
    """Decode the raw Snappy block encoding used by LevelDB."""

    expected, pos = _read_varint(data, 0)
    out = bytearray()
    while pos < len(data) and len(out) < expected:
        tag = data[pos]
        pos += 1
        kind = tag & 0x03
        if kind == 0:
            length_code = tag >> 2
            if length_code < 60:
                length = length_code + 1
            else:
                extra = length_code - 59
                if pos + extra > len(data):
                    raise LevelDBFormatError("truncated Snappy literal length")
                length = int.from_bytes(data[pos:pos + extra], "little") + 1
                pos += extra
            end = pos + length
            if end > len(data):
                raise LevelDBFormatError("truncated Snappy literal")
            out.extend(data[pos:end])
            pos = end
            continue

        if kind == 1:
            if pos >= len(data):
                raise LevelDBFormatError("truncated Snappy one-byte copy")
            length = 4 + ((tag >> 2) & 0x07)
            offset = ((tag & 0xE0) << 3) | data[pos]
            pos += 1
        elif kind == 2:
            if pos + 2 > len(data):
                raise LevelDBFormatError("truncated Snappy two-byte copy")
            length = 1 + (tag >> 2)
            offset = int.from_bytes(data[pos:pos + 2], "little")
            pos += 2
        else:
            if pos + 4 > len(data):
                raise LevelDBFormatError("truncated Snappy four-byte copy")
            length = 1 + (tag >> 2)
            offset = int.from_bytes(data[pos:pos + 4], "little")
            pos += 4

        if offset <= 0 or offset > len(out):
            raise LevelDBFormatError("invalid Snappy copy offset")
        for _ in range(length):
            out.append(out[-offset])

    if len(out) != expected:
        raise LevelDBFormatError(
            f"Snappy size mismatch: expected {expected}, decoded {len(out)}"
        )
    return bytes(out)


def _decode_block_entries(block: bytes) -> Iterator[tuple[bytes, bytes]]:
    if len(block) < 4:
        raise LevelDBFormatError("LevelDB block is too small")
    restart_count = struct.unpack_from("<I", block, len(block) - 4)[0]
    restart_bytes = restart_count * 4
    entries_end = len(block) - 4 - restart_bytes
    if entries_end < 0:
        raise LevelDBFormatError("invalid LevelDB restart table")

    pos = 0
    previous_key = b""
    while pos < entries_end:
        shared, pos = _read_varint(block, pos, entries_end)
        non_shared, pos = _read_varint(block, pos, entries_end)
        value_size, pos = _read_varint(block, pos, entries_end)
        if shared > len(previous_key):
            raise LevelDBFormatError("invalid shared-key prefix")
        key_end = pos + non_shared
        value_end = key_end + value_size
        if value_end > entries_end:
            raise LevelDBFormatError("truncated LevelDB block entry")
        key = previous_key[:shared] + block[pos:key_end]
        value = block[key_end:value_end]
        yield key, value
        previous_key = key
        pos = value_end


def _decode_block_handle(data: bytes) -> tuple[int, int]:
    offset, pos = _read_varint(data, 0)
    size, _ = _read_varint(data, pos)
    return offset, size


def _read_table_block(table: bytes, offset: int, size: int) -> bytes:
    end = offset + size
    trailer_end = end + BLOCK_TRAILER_SIZE
    if offset < 0 or size < 0 or trailer_end > len(table):
        raise LevelDBFormatError("block handle points outside table")
    raw = table[offset:end]
    compression = table[end]
    if compression == 0:
        return raw
    if compression == 1:
        return _snappy_decompress(raw)
    raise LevelDBFormatError(f"unsupported LevelDB compression type: {compression}")


def iter_table_records(path: Path) -> Iterator[tuple[bytes, int, int, bytes]]:
    """Yield (user_key, sequence, value_type, value) from an SSTable."""

    table = path.read_bytes()
    if len(table) < FOOTER_SIZE:
        raise LevelDBFormatError(f"table is too small: {path}")
    footer = table[-FOOTER_SIZE:]
    magic = struct.unpack_from("<Q", footer, FOOTER_SIZE - 8)[0]
    if magic != LEVELDB_MAGIC:
        raise LevelDBFormatError(f"bad LevelDB table magic: {path}")

    _, pos = _read_varint(footer, 0, FOOTER_SIZE - 8)
    _, pos = _read_varint(footer, pos, FOOTER_SIZE - 8)
    index_offset, pos = _read_varint(footer, pos, FOOTER_SIZE - 8)
    index_size, _ = _read_varint(footer, pos, FOOTER_SIZE - 8)
    index_block = _read_table_block(table, index_offset, index_size)

    for _, handle in _decode_block_entries(index_block):
        block_offset, block_size = _decode_block_handle(handle)
        data_block = _read_table_block(table, block_offset, block_size)
        for internal_key, value in _decode_block_entries(data_block):
            if len(internal_key) < 8:
                raise LevelDBFormatError(f"short internal key in {path}")
            trailer = int.from_bytes(internal_key[-8:], "little")
            yield internal_key[:-8], trailer >> 8, trailer & 0xFF, value


def _iter_logical_log_records(data: bytes) -> Iterator[bytes]:
    pos = 0
    fragments: bytearray | None = None
    while pos + 7 <= len(data):
        block_left = LOG_BLOCK_SIZE - (pos % LOG_BLOCK_SIZE)
        if block_left < 7:
            pos += block_left
            continue
        _, length, record_type = struct.unpack_from("<IHB", data, pos)
        pos += 7
        if length == 0 and record_type == 0:
            pos += LOG_BLOCK_SIZE - (pos % LOG_BLOCK_SIZE)
            continue
        end = pos + length
        if end > len(data) or length > block_left - 7:
            raise LevelDBFormatError("truncated LevelDB log record")
        payload = data[pos:end]
        pos = end

        if record_type == 1:  # FULL
            fragments = None
            yield payload
        elif record_type == 2:  # FIRST
            fragments = bytearray(payload)
        elif record_type == 3:  # MIDDLE
            if fragments is None:
                raise LevelDBFormatError("orphan LevelDB log middle fragment")
            fragments.extend(payload)
        elif record_type == 4:  # LAST
            if fragments is None:
                raise LevelDBFormatError("orphan LevelDB log last fragment")
            fragments.extend(payload)
            yield bytes(fragments)
            fragments = None
        else:
            raise LevelDBFormatError(f"unknown LevelDB log record type: {record_type}")


def iter_log_records(path: Path) -> Iterator[tuple[bytes, int, int, bytes]]:
    """Yield logical entries from a LevelDB write-ahead log."""

    for batch in _iter_logical_log_records(path.read_bytes()):
        if len(batch) < 12:
            raise LevelDBFormatError(f"short write batch in {path}")
        sequence, count = struct.unpack_from("<QI", batch, 0)
        pos = 12
        for index in range(count):
            if pos >= len(batch):
                raise LevelDBFormatError(f"truncated write batch in {path}")
            value_type = batch[pos]
            pos += 1
            key, pos = _read_length_prefixed(batch, pos)
            value = b""
            if value_type == 1:
                value, pos = _read_length_prefixed(batch, pos)
            elif value_type != 0:
                raise LevelDBFormatError(f"unknown write-batch tag: {value_type}")
            yield key, sequence + index, value_type, value


def decode_wetype_pair_key(key: bytes, sequence: int) -> WeTypeWord | None:
    if not key.startswith(WETYPE_USER_PAIR_PREFIX):
        return None
    payload = key[len(WETYPE_USER_PAIR_PREFIX):]
    pinyin_raw, separator, word_raw = payload.partition(b"\x01")
    if not separator or not pinyin_raw or not word_raw:
        raise LevelDBFormatError("malformed WeType user pair key")
    try:
        pinyin = pinyin_raw.decode("ascii").replace(",", "'").lower()
        word = word_raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LevelDBFormatError("invalid text encoding in WeType pair key") from exc
    if not re.fullmatch(r"[a-z']+", pinyin):
        raise LevelDBFormatError("invalid pinyin in WeType pair key")
    return WeTypeWord(pinyin=pinyin, word=word, sequence=sequence)


def scan_wetype_leveldb(path: Path) -> tuple[list[WeTypeWord], ScanStats]:
    """Read current WeType pair records, resolving updates and tombstones."""

    if not (path / "CURRENT").is_file():
        raise FileNotFoundError(f"not a LevelDB directory (CURRENT missing): {path}")

    table_paths = sorted([*path.glob("*.ldb"), *path.glob("*.sst")])
    log_paths = sorted(path.glob("*.log"))
    latest: dict[bytes, tuple[int, int]] = {}
    physical_records = 0

    def consume(records: Iterator[tuple[bytes, int, int, bytes]]) -> None:
        nonlocal physical_records
        for key, sequence, value_type, _ in records:
            physical_records += 1
            if not key.startswith(WETYPE_USER_PAIR_PREFIX):
                continue
            previous = latest.get(key)
            if previous is None or sequence > previous[0]:
                latest[key] = (sequence, value_type)

    for table_path in table_paths:
        consume(iter_table_records(table_path))
    for log_path in log_paths:
        consume(iter_log_records(log_path))

    words: list[WeTypeWord] = []
    deleted = 0
    malformed = 0
    for key, (sequence, value_type) in latest.items():
        if value_type == 0:
            deleted += 1
            continue
        try:
            decoded = decode_wetype_pair_key(key, sequence)
        except LevelDBFormatError:
            malformed += 1
            continue
        if decoded is not None:
            words.append(decoded)
    words.sort(key=lambda item: (item.sequence, item.pinyin, item.word))
    return words, ScanStats(
        table_files=len(table_paths),
        log_files=len(log_paths),
        physical_records=physical_records,
        live_pair_keys=len(words),
        deleted_pair_keys=deleted,
        malformed_pair_keys=malformed,
    )
