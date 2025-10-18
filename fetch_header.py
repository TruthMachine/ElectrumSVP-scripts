#!/usr/bin/env python3
import asyncio
import ssl
import json

SERVER = 'electrumx.gorillapool.io'
PORT = 50002
CERT_FILE = 'gorillapool.pem'

async def fetch_header(height=0):
    ssl_ctx = ssl.create_default_context(cafile=CERT_FILE)
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_REQUIRED

    print(f"Connecting to {SERVER}:{PORT} (SSL)...")
    reader, writer = await asyncio.open_connection(SERVER, PORT, ssl=ssl_ctx)

    try:
        request = json.dumps({
            'id': 0,
            'method': 'blockchain.block.header',
            'params': [height]
        }) + '\n'

        writer.write(request.encode())
        await writer.drain()

        response = await reader.readline()
        data = json.loads(response.decode())
        print(f"Header at height {height}:")
        print(json.dumps(data, indent=4))

    finally:
        writer.close()
        await writer.wait_closed()

if __name__ == '__main__':
    asyncio.run(fetch_header())

