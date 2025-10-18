#!/usr/bin/env python3
import sys
import json
import struct
from hashlib import sha256
from datetime import datetime

# --- Utilities ---
def double_sha256(b: bytes) -> bytes:
    return sha256(sha256(b).digest()).digest()

def parse_extraced_block_header(header_hex: str):
    header_bytes = bytes.fromhex(header_hex)
    if len(header_bytes) != 80:
        raise ValueError(f"Invalid header length: {len(header_bytes)} (expected 80 bytes)")
    version, = struct.unpack("<I", header_bytes[0:4])
    prev_block = header_bytes[4:36][::-1].hex()
    merkle_root = header_bytes[36:68][::-1].hex()
    timestamp, bits, nonce = struct.unpack("<III", header_bytes[68:80])
    block_hash = double_sha256(header_bytes)[::-1].hex()
    return {
        "version": version,
        "prev_block": prev_block,
        "merkle_root": merkle_root,
        "timestamp": timestamp,
        "timestamp_iso": datetime.utcfromtimestamp(timestamp).isoformat() + "Z",
        "bits": bits,
        "nonce": nonce,
        "block_hash": block_hash
    }

def parse_beef(beef_path: str):
    with open(beef_path, "r") as f:
        beef = json.load(f)
    for utxo in beef.get("utxos", []):
        header_hex = utxo.get("header")
        if header_hex:
            try:
                utxo["parsed_header"] = parse_extraced_block_header(header_hex)
            except Exception as e:
                utxo["parsed_header"] = {"error": str(e)}
    return beef

# --- Main ---
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: parse_beef.py <beef.json> or <header_hex>")
        sys.exit(1)

    arg = sys.argv[1]

    # detect if it looks like JSON (starts with { or [)
    if arg.strip().endswith(".json"):
        beef_parsed = parse_beef(arg)
        print(json.dumps(beef_parsed, indent=2))
    else:
        # assume raw 80-byte header hex
        try:
            parsed_header = parse_extraced_block_header(arg)
            print(json.dumps(parsed_header, indent=2))
        except Exception as e:
            print(f"Error parsing header: {e}")

