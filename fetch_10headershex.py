#!/usr/bin/env python3
import asyncio
import ssl
import json

SERVER = "electrumx.gorillapool.io"
PORT = 50002  # SSL port
NUM_HEADERS = 10

async def fetch_headers():
    # Create SSL context that ignores certificate verification
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    print(f"Connecting to {SERVER}:{PORT} (SSL)...")
    reader, writer = await asyncio.open_connection(SERVER, PORT, ssl=ssl_ctx)

    # ElectrumX method: blockchain.block.headers(start_height, count)
    request = {
        "jsonrpc": "2.0",
        "method": "blockchain.block.headers",
        "params": [0, NUM_HEADERS],
        "id": 0
    }

    # Send request
    writer.write((json.dumps(request) + "\n").encode())
    await writer.drain()

    # Read response
    line = await reader.readline()
    response = json.loads(line.decode())

    if "error" in response:
        print("Error from server:", response["error"])
    else:
        hex_headers = response["result"]["hex"]
        print(f"Headers (hex): {hex_headers}")

    writer.close()
    await writer.wait_closed()

if __name__ == "__main__":
    asyncio.run(fetch_headers())

