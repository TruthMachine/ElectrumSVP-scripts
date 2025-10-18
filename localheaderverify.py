import json
import hashlib
import os

# Auto-detect headers file path
POSSIBLE_HEADER_PATHS = [
    os.path.expanduser("~/.electrum-sv/headers"),
    os.path.expanduser("~/.electrum-sv/headers-electrumsv"),
    os.path.expanduser("~/.electrumsv/headers"),
]

def find_headers_file():
    for path in POSSIBLE_HEADER_PATHS:
        if os.path.exists(path):
            return path
    raise FileNotFoundError("No headers file found in expected locations.")

HEADERS_PATH = find_headers_file()

def double_sha256(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()

def le(hex_str: str) -> bytes:
    """Convert hex string to little-endian bytes"""
    return bytes.fromhex(hex_str)[::-1]

def compute_merkle_root(txid: str, merkle_branch: list, pos: int) -> bytes:
    h = le(txid)
    for branch_hex in merkle_branch:
        branch = le(branch_hex)
        if pos & 1 == 0:
            h = double_sha256(h + branch)
        else:
            h = double_sha256(branch + h)
        pos >>= 1
    return h

def read_header_from_file(height: int) -> bytes:
    """Reads 80-byte block header from headers file by height"""
    offset = height * 80
    with open(HEADERS_PATH, "rb") as f:
        f.seek(offset)
        header = f.read(80)
        if len(header) != 80:
            raise ValueError(f"Header for block {height} not found in file.")
        return header

def merkle_root_from_header(header_bytes: bytes) -> bytes:
    return header_bytes[36:68]

def main():
    with open("beef.json") as f:
        data = json.load(f)

    utxos = data.get("utxos", [])
    for utxo in utxos:
        txid = utxo["txid"]
        blockheight = utxo["blockheight"]
        merkle_info = utxo.get("merkle")

        if not merkle_info:
            print(f"No merkle info for txid {txid}")
            continue

        merkle_branch = merkle_info["merkle"]
        pos = merkle_info["pos"]

        # Read header from local headers file
        header_bytes = read_header_from_file(blockheight)

        computed_root = compute_merkle_root(txid, merkle_branch, pos)
        header_root = merkle_root_from_header(header_bytes)

        print(f"\n--- Verifying txid: {txid} ---")
        print(f"Computed Merkle root (BE): {computed_root[::-1].hex()}")
        print(f"Merkle root in header (BE): {header_root[::-1].hex()}")

        if computed_root == header_root:
            print(f"Block {blockheight} inclusion: ✅ Verified (using local headers file)")
        else:
            print(f"Block {blockheight} inclusion: ❌ INVALID")

if __name__ == "__main__":
    main()

