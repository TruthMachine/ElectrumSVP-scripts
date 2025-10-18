import json
import hashlib

def double_sha256(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()

def le(hex_str: str) -> bytes:
    """Convert hex string to little-endian bytes"""
    return bytes.fromhex(hex_str)[::-1]

def compute_merkle_root(txid: str, merkle_branch: list, pos: int) -> bytes:
    h = le(txid)  # little-endian
    for branch_hex in merkle_branch:
        branch = le(branch_hex)
        if pos & 1 == 0:
            h = double_sha256(h + branch)
        else:
            h = double_sha256(branch + h)
        pos >>= 1
    return h  # little-endian bytes

def merkle_root_from_header(header_hex: str) -> bytes:
    """Extract Merkle root (32 bytes) from 80-byte block header"""
    header_bytes = bytes.fromhex(header_hex)
    # In Bitcoin headers: merkle root is bytes 36..68 (32 bytes), little-endian in header
    return header_bytes[36:68]

def main():
    with open("beef.json") as f:
        data = json.load(f)

    utxos = data.get("utxos", [])
    for utxo in utxos:
        txid = utxo["txid"]
        blockheight = utxo["blockheight"]
        merkle_info = utxo.get("merkle")
        header_hex = utxo.get("header")

        if not merkle_info or not header_hex:
            print(f"No merkle/header info for txid {txid}")
            continue

        merkle_branch = merkle_info["merkle"]
        pos = merkle_info["pos"]

        computed_root = compute_merkle_root(txid, merkle_branch, pos)
        header_root = merkle_root_from_header(header_hex)

        print(f"\n--- Verifying txid: {txid} ---")
        print(f"Computed Merkle root (BE): {computed_root[::-1].hex()}")
        print(f"Merkle root in header (BE): {header_root[::-1].hex()}")

        if computed_root == header_root:
            print(f"Block {blockheight} inclusion: ✅ Verified")
        else:
            print(f"Block {blockheight} inclusion: ❌ INVALID")

if __name__ == "__main__":
    main()

