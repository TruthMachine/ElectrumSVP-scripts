#!/usr/bin/env python3
import sys
import json
import socket
import ssl
from hashlib import sha256
from binascii import unhexlify, hexlify

SERVER = "electrumx.gorillapool.io"
PORT = 50002
TIMEOUT = 30

def double_sha256(b: bytes) -> bytes:
    return sha256(sha256(b).digest()).digest()

def electrum_request(method, params):
    """Send JSON-RPC request over SSL to ElectrumX."""
    req = {"id": 0, "method": method, "params": params}
    msg = (json.dumps(req) + "\n").encode()

    context = ssl._create_unverified_context()
    with socket.create_connection((SERVER, PORT), timeout=TIMEOUT) as sock:
        with context.wrap_socket(sock, server_hostname=SERVER) as ssock:
            ssock.sendall(msg)
            data = b""
            while not data.endswith(b"\n"):
                chunk = ssock.recv(4096)
                if not chunk:
                    break
                data += chunk
            return json.loads(data.decode())["result"]

def merkle_root_from_header(header_hex: str) -> bytes:
    """
    Extract Merkle root from block header returned by ElectrumX.
    ElectrumX returns the header hex in big-endian.
    Bytes 36-68 are the Merkle root in little-endian inside the header.
    We reverse it to big-endian for comparison.
    """
    header_bytes = unhexlify(header_hex)
    merkle_root_le = header_bytes[36:68]
    return merkle_root_le[::-1]  # convert to big-endian

def verify_merkle(txid_hex: str, merkle: dict, merkle_root: bytes) -> bool:
    """
    Verify a transaction against a Merkle branch.
    txid_hex: big-endian hex
    merkle: dict with "merkle" (branch list) and "pos"
    merkle_root: bytes (big-endian) from block header
    """
    print(f"\n--- Verifying txid: {txid_hex} ---")
    print(f"Original header merkle root (hex): {hexlify(merkle_root).decode()}")
    
    h = unhexlify(txid_hex)[::-1]  # convert txid to little-endian
    pos = merkle["pos"]
    branch = [unhexlify(x)[::-1] for x in merkle["merkle"]]  # little-endian branch

    print(f"Txid (LE): {hexlify(h).decode()}")
    print(f"Merkle branch positions: {pos}, {len(branch)} hashes")
    for i, b in enumerate(branch):
        print(f"Branch[{i}] (LE): {hexlify(b).decode()}")

    for i, b in enumerate(branch):
        if pos % 2 == 0:
            h = double_sha256(h + b)
            print(f"Step {i}: hash = double_sha256(h + branch) -> {hexlify(h).decode()}")
        else:
            h = double_sha256(b + h)
            print(f"Step {i}: hash = double_sha256(branch + h) -> {hexlify(h).decode()}")
        pos //= 2

    # computed root is little-endian; reverse to big-endian for comparison
    computed_root_be = h[::-1]
    print(f"Computed Merkle root (BE): {hexlify(computed_root_be).decode()}")
    included = computed_root_be == merkle_root
    print(f"Included? {included}")
    return included

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: merkleproof_verify.py <beef.json>")
        sys.exit(1)

    beef_file = sys.argv[1]
    with open(beef_file, "r") as f:
        beef = json.load(f)

    for utxo in beef.get("utxos", []):
        txid = utxo["txid"]
        merkle = utxo.get("merkle")
        height = utxo.get("blockheight", -1)

        if not merkle or height <= 0:
            print(f"{txid} @ block {height}: included = False (no proof)")
            continue

        try:
            header_hex = electrum_request("blockchain.block.header", [height])
        except Exception as e:
            print(f"{txid} @ block {height}: error fetching header: {e}")
            continue

        merkle_root = merkle_root_from_header(header_hex)
        included = verify_merkle(txid, merkle, merkle_root)
        print(f"{txid} @ block {height}: included = {included}")

