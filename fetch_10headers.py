#!/usr/bin/env python3


import asyncio
import ssl
import json
import struct
import binascii

SERVER = 'electrumx.gorillapool.io'
PORT = 50002
NUM_HEADERS = 10

def parse_header(hex_header):
    header = bytes.fromhex(hex_header)
    version, = struct.unpack('<I', header[0:4])
    prev_block = header[4:36][::-1].hex()
    merkle_root = header[36:68][::-1].hex()
    timestamp, = struct.unpack('<I', header[68:72])
    bits, = struct.unpack('<I', header[72:76])
    nonce, = struct.unpack('<I', header[76:80])
    return {
        'version': version,
        'prev_block': prev_block,
        'merkle_root': merkle_root,
        'timestamp': timestamp,
        'bits': bits,
        'nonce': nonce
    }

async def fetch_headers():
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    reader, writer = await asyncio.open_connection(SERVER, PORT, ssl=ssl_ctx)
    headers = []

    for height in range(NUM_HEADERS):
        request = {
            "jsonrpc": "2.0",
            "method": "blockchain.block.header",
            "params": [height],
            "id": height
        }
        writer.write((json.dumps(request) + "\n").encode())
        await writer.drain()

        line = await reader.readline()
        if not line:
            continue
        response = json.loads(line.decode())
        if "result" in response:
            headers.append(parse_header(response["result"]))

    writer.close()
    await writer.wait_closed()
    return headers

async def main():
    headers = await fetch_headers()
    for i, h in enumerate(headers):
        print(f"Header {i}:")
        for k, v in h.items():
            print(f"  {k}: {v}")
        print()

asyncio.run(main())

