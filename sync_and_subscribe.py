#!/usr/bin/env python3
import asyncio
import ssl
import binascii
import json
import os
import hashlib
import struct

# ElectrumX server and port
SERVER = "electrumx.gorillapool.io"
PORT = 50002  # SSL port

# Path to headers file
HEADERS_FILE = os.path.expanduser("~/.electrum-sv/headers")

# Genesis block hash and header hex
GENESIS_HASH = "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"
GENESIS_HEADER_HEX = (
    "01000000"  # version
    "0000000000000000000000000000000000000000000000000000000000000000"  # prev_hash
    "3ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a"  # merkle root
    "29ab5f49"  # timestamp
    "ffff001d"  # bits
    "1dac2b7c"  # nonce
)

# ----- Helpers -----

def double_sha256(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()

def bits_to_target(bits: int) -> int:
    exponent = bits >> 24
    mantissa = bits & 0xFFFFFF
    return mantissa * (1 << (8 * (exponent - 3)))

def verify_header(header_bytes: bytes):
    """Verify PoW"""
    version, prev_hash_raw, merkle_root_raw, timestamp, bits, nonce = struct.unpack("<I32s32sIII", header_bytes)
    header_hash = double_sha256(header_bytes)[::-1].hex()
    target = bits_to_target(bits)
    if int(header_hash, 16) > target:
        raise RuntimeError(f"Invalid PoW for header {header_hash}")
    return header_hash

def verify_header_sequence(header_bytes: bytes, prev_bytes: bytes):
    """Verify prev_hash linkage"""
    if prev_bytes is None:
        return  # first header (genesis) has no previous
    prev_hash = double_sha256(prev_bytes)[::-1].hex()
    header_prev_hash = header_bytes[4:36][::-1].hex()
    if header_prev_hash != prev_hash:
        raise RuntimeError("Invalid prev_hash linkage")

def read_existing_tip():
    if not os.path.exists(HEADERS_FILE) or os.path.getsize(HEADERS_FILE) < 80:
        print("Headers file missing or too small, initializing with genesis block...")
        genesis_bytes = binascii.unhexlify(GENESIS_HEADER_HEX)
        os.makedirs(os.path.dirname(HEADERS_FILE), exist_ok=True)
        with open(HEADERS_FILE, "wb") as f:
            f.write(genesis_bytes)
        return GENESIS_HASH, 0
    with open(HEADERS_FILE, "rb") as f:
        data = f.read()
        last_header = data[-80:]
        last_height = len(data) // 80 - 1
        header_hash = double_sha256(last_header)[::-1].hex()
        return header_hash, last_height

def append_header_bytes(header_bytes: bytes):
    with open(HEADERS_FILE, "ab") as f:
        f.write(header_bytes)

# ----- Networking -----

async def fetch_chunk(start_height: int, count: int) -> bytes:
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    reader, writer = await asyncio.open_connection(SERVER, PORT, ssl=ssl_ctx)
    request = {
        "jsonrpc": "2.0",
        "method": "blockchain.block.headers",
        "params": [start_height, count],
        "id": start_height
    }
    writer.write((json.dumps(request) + "\n").encode())
    await writer.drain()
    line = await reader.readline()
    writer.close()
    await writer.wait_closed()
    response = json.loads(line.decode())
    if "error" in response:
        raise RuntimeError(response["error"])
    hex_headers = response["result"]["hex"]
    return binascii.unhexlify(hex_headers)

# ----- Sync -----

async def sync_headers(chunk_size=400):
    tip_hash, tip_height = read_existing_tip()
    print(f"Current tip height: {tip_height}, hash: {tip_hash}")

    while True:
        try:
            headers_bytes = await fetch_chunk(tip_height + 1, chunk_size)
        except RuntimeError:
            print("No more headers returned; sync complete.")
            break
        num_headers = len(headers_bytes) // 80
        if num_headers == 0:
            print(f"No new headers returned; synced to height {tip_height}")
            break
        last_header_bytes = None
        if tip_height > 0:
            with open(HEADERS_FILE, "rb") as f:
                f.seek((tip_height) * 80)
                last_header_bytes = f.read(80)
        for i in range(num_headers):
            header = headers_bytes[i*80:(i+1)*80]
            verify_header_sequence(header, last_header_bytes)
            header_hash = verify_header(header)
            append_header_bytes(header)
            tip_height += 1
            last_header_bytes = header
            print(f"Appended header at height {tip_height} ({header_hash[:16]}...)")
    print(f"Headers fully synced to height {tip_height}")

# ----- Subscription -----

async def subscribe_to_headers():
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    while True:
        try:
            reader, writer = await asyncio.open_connection(SERVER, PORT, ssl=ssl_ctx)
            sub_request = {
                "jsonrpc": "2.0",
                "method": "blockchain.headers.subscribe",
                "params": [],
                "id": 1
            }
            writer.write((json.dumps(sub_request) + "\n").encode())
            await writer.drain()
            print("Subscribed to new block headers...")

            while True:
                line = await reader.readline()
                if not line:
                    print("Server closed connection. Reconnecting...")
                    break
                try:
                    msg = json.loads(line.decode())
                except json.JSONDecodeError:
                    continue

                # Handle push notifications
                if "method" in msg and msg["method"] == "blockchain.headers.subscribe":
                    header_info = msg["params"][0]
                    header_hex = header_info["hex"]
                    height = header_info["height"]

                    tip_hash, tip_height = read_existing_tip()
                    if height <= tip_height:
                        continue

                    header_bytes = binascii.unhexlify(header_hex)
                    last_header_bytes = None
                    if tip_height > 0:
                        with open(HEADERS_FILE, "rb") as f:
                            f.seek(tip_height * 80)
                            last_header_bytes = f.read(80)
                    verify_header_sequence(header_bytes, last_header_bytes)
                    header_hash = verify_header(header_bytes)
                    append_header_bytes(header_bytes)
                    print(f"Appended new header at height {height} ({header_hash[:16]}...)")

        except Exception as e:
            print(f"Error in subscription loop: {e}")
            await asyncio.sleep(5)

# ----- Main -----

async def main():
    await sync_headers()
    await subscribe_to_headers()

if __name__ == "__main__":
    asyncio.run(main())

