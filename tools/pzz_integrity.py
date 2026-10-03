"""NEXT PLUS PZZ loader checksum over the decoded, word-aligned body.

The original loader at 0x088BD728 accumulates unsigned words into a 64-bit
sum seeded by ((body_bytes * 7) & 0xffffffff) >> 1, and XORs every prefix sum
into an all-ones accumulator. Its wrapper at 0x088BD520 compares all 16 bytes.
The trailer is stored directly, without the body's XOR transform.
"""
import struct

MASK64 = (1 << 64) - 1


def checksum_trailer(decoded_body: bytes) -> bytes:
    if len(decoded_body) % 4:
        raise ValueError('Only the observed word-aligned PZZ variant is supported')
    total = ((len(decoded_body) * 7) & 0xffffffff) >> 1
    prefixes = MASK64
    for (word,) in struct.iter_unpack('<I', decoded_body):
        total = (total + word) & MASK64
        prefixes ^= total
    return struct.pack('<QQ', total, prefixes)


def verify_trailer(encoded: bytes, decoded: bytes) -> bool:
    if len(encoded) != len(decoded) or len(encoded) < 16:
        return False
    return checksum_trailer(decoded[:-16]) == encoded[-16:]
