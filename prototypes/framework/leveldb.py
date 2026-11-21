"""Chrome's LevelDB stores read from disk, for the diagnostic's profile scan
(docs/framework_prototype.md §2.5.3, "bytes on disk after close").

Local Storage, Session Storage and IndexedDB keep their data in LevelDB: a
write-ahead log (`*.log`) of write batches and sorted tables (`*.ldb`) whose
blocks may be Snappy-compressed. This reads both, raw Snappy included, and
yields every key and value — the values as stored, which for IndexedDB are V8
serializations the inspection then reads as bytes.
"""

from __future__ import annotations

import pathlib
import struct


class Unreadable(Exception):
    pass


def _varint(data: bytes, pos: int) -> tuple[int, int]:
    result = shift = 0
    while True:
        if pos >= len(data):
            raise Unreadable("a varint runs past the end")
        b = data[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not b & 0x80:
            return result, pos
        shift += 7
        if shift > 63:
            raise Unreadable("a varint is too long")


def snappy(data: bytes) -> bytes:
    """Raw Snappy (the block format LevelDB uses)."""
    size, pos = _varint(data, 0)
    out = bytearray()
    while pos < len(data):
        tag = data[pos]
        pos += 1
        kind = tag & 3
        if kind == 0:
            length = tag >> 2
            if length >= 60:
                extra = length - 59
                length = int.from_bytes(data[pos:pos + extra], "little")
                pos += extra
            length += 1
            out += data[pos:pos + length]
            pos += length
            continue
        if kind == 1:
            length = ((tag >> 2) & 7) + 4
            offset = ((tag >> 5) << 8) | data[pos]
            pos += 1
        elif kind == 2:
            length = (tag >> 2) + 1
            offset = int.from_bytes(data[pos:pos + 2], "little")
            pos += 2
        else:
            length = (tag >> 2) + 1
            offset = int.from_bytes(data[pos:pos + 4], "little")
            pos += 4
        if offset == 0 or offset > len(out):
            raise Unreadable("a Snappy copy points outside the output")
        for _ in range(length):
            out.append(out[-offset])
    if len(out) != size:
        raise Unreadable("Snappy output of the wrong length")
    return bytes(out)


def _batch(record: bytes):
    if len(record) < 12:
        return
    count = struct.unpack_from("<I", record, 8)[0]
    pos = 12
    for _ in range(count):
        tag = record[pos]
        pos += 1
        klen, pos = _varint(record, pos)
        key = record[pos:pos + klen]
        pos += klen
        if tag == 1:
            vlen, pos = _varint(record, pos)
            yield key, record[pos:pos + vlen]
            pos += vlen
        else:
            yield key, b""


def read_log(data: bytes):
    """The log's 32 KiB blocks of records (full, first, middle, last)."""
    pos, pending = 0, bytearray()
    while pos + 7 <= len(data):
        block_left = 32768 - pos % 32768
        if block_left < 7:
            pos += block_left
            continue
        length, kind = struct.unpack_from("<HB", data, pos + 4)
        payload = data[pos + 7:pos + 7 + length]
        pos += 7 + length
        if kind == 0 and length == 0:
            pos += 32768 - pos % 32768 if pos % 32768 else 0
            continue
        if kind == 1:
            yield from _batch(payload)
        elif kind == 2:
            pending = bytearray(payload)
        elif kind == 3:
            pending += payload
        elif kind == 4:
            pending += payload
            yield from _batch(bytes(pending))
            pending = bytearray()


def _block(data: bytes, offset: int, size: int) -> bytes:
    raw = data[offset:offset + size]
    kind = data[offset + size]
    if kind == 0:
        return raw
    if kind == 1:
        return snappy(raw)
    raise Unreadable(f"a block compressed with type {kind}")


def _entries(block: bytes):
    restarts = struct.unpack_from("<I", block, len(block) - 4)[0]
    end = len(block) - 4 - 4 * restarts
    pos, key = 0, b""
    while pos < end:
        shared, pos = _varint(block, pos)
        unshared, pos = _varint(block, pos)
        vlen, pos = _varint(block, pos)
        key = key[:shared] + block[pos:pos + unshared]
        pos += unshared
        yield key, block[pos:pos + vlen]
        pos += vlen


def read_table(data: bytes):
    """A sorted table: the footer's index handle, each data block through it."""
    if len(data) < 48 or data[-8:] != bytes.fromhex("57fb808b247547db"):
        raise Unreadable("not a LevelDB table")
    footer = data[-48:]
    _, pos = _varint(footer, 0)
    _, pos = _varint(footer, pos)
    index_offset, pos = _varint(footer, pos)
    index_size, _ = _varint(footer, pos)
    for _, handle in _entries(_block(data, index_offset, index_size)):
        offset, p = _varint(handle, 0)
        size, _ = _varint(handle, p)
        for key, value in _entries(_block(data, offset, size)):
            yield key[:-8] if len(key) >= 8 else key, value  # the 8-byte sequence and type


def read(path: pathlib.Path):
    data = path.read_bytes()
    if path.suffix == ".log":
        yield from read_log(data)
    elif path.suffix in (".ldb", ".sst"):
        yield from read_table(data)
