#!/usr/bin/env python3
import socket
import ssl
import json
import sys
from hashlib import sha256
from bitcoinx import Address, Bitcoin

# --- ElectrumX server config ---
SERVER = "electrumx.gorillapool.io"
PORT = 50002  # SSL
TIMEOUT = 30  # seconds, for VMs or slow networks

# --- Utilities ---
def scripthash_from_address(address: str) -> str:
    """Convert an address to ElectrumX scripthash format (little-endian SHA256 of script)."""
    addr = Address.from_string(address, Bitcoin)
    script_bytes = addr.to_script().to_bytes()
    return sha256(script_bytes).digest()[::-1].hex()

def electrum_request(method, params):
    """Send a JSON-RPC request to the ElectrumX server."""
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
            return json.loads(data.decode())

# --- Main extractor ---
def get_beef(address: str, include_merkle=True):
    scripthash = scripthash_from_address(address)
    print(f"Querying {SERVER}:{PORT} for scripthash {scripthash} ...", file=sys.stderr)

    utxos = electrum_request("blockchain.scripthash.listunspent", [scripthash]).get("result", [])
    beef_utxos = []

    for utxo in utxos:
        utxo_entry = {
            "txid": utxo["tx_hash"],
            "vout": utxo["tx_pos"],
            "satoshis": utxo["value"],
            "blockheight": utxo.get("height", -1)
        }

        # Optional merkle proof
        if include_merkle and utxo_entry["blockheight"] > 0:
            try:
                merkle_resp = electrum_request(
                    "blockchain.transaction.get_merkle",
                    [utxo_entry["txid"], utxo_entry["blockheight"]]
                )
                utxo_entry["merkle"] = merkle_resp.get("result")
            except Exception:
                utxo_entry["merkle"] = None

            # Fetch 80-byte raw block header
            try:
                header_resp = electrum_request(
                    "blockchain.block.header",
                    [utxo_entry["blockheight"]]
                )
                utxo_entry["header"] = header_resp.get("result")  # raw 80-byte hex
            except Exception:
                utxo_entry["header"] = None

        beef_utxos.append(utxo_entry)

    return {
        "format": "BEEF",
        "version": 1,
        "address": address,
        "utxos": beef_utxos
    }

# --- Command line ---
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: beef_extract.py <address>")
        sys.exit(1)

    address = sys.argv[1]
    beef = get_beef(address)
    print(json.dumps(beef, indent=2))

