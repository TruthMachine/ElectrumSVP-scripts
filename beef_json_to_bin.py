#!/usr/bin/env python3
import json
import struct
import sys

def json_to_binary_beef(json_obj):
    data = b""

    # 1. Magic number: 0x0100BEEF (little-endian)
    data += struct.pack("<I", 0x0100BEEF)

    # 2. Version: 2 bytes, little-endian
    data += struct.pack("<H", json_obj.get("version", 1))

    # 3. Address length + address
    address_bytes = json_obj["address"].encode("ascii")
    if len(address_bytes) > 255:
        raise ValueError("Address too long")
    data += struct.pack("B", len(address_bytes))
    data += address_bytes

    # 4. Number of UTXOs: 4 bytes, little-endian
    utxos = json_obj["utxos"]
    data += struct.pack("<I", len(utxos))

    for utxo in utxos:
        # TXID: 32 bytes (reversed for internal representation)
        txid_bytes = bytes.fromhex(utxo["txid"])[::-1]
        data += txid_bytes

        # VOUT: 4 bytes
        data += struct.pack("<I", utxo["vout"])

        # Satoshis: 8 bytes
        data += struct.pack("<Q", utxo["satoshis"])

        # Blockheight: 4 bytes
        data += struct.pack("<I", utxo["blockheight"])

        # Merkle proof
        merkle = utxo.get("merkle")
        if merkle:
            hashes = merkle.get("merkle", [])
            # Number of merkle hashes: 4 bytes
            data += struct.pack("<I", len(hashes))
            for h in hashes:
                # Each hash: 32 bytes, reversed
                data += bytes.fromhex(h)[::-1]
            # Position: 4 bytes
            data += struct.pack("<I", merkle.get("pos", 0))
        else:
            # Zero merkle entries
            data += struct.pack("<I", 0)
            # No position
            data += struct.pack("<I", 0)

        # Block header: 80 bytes
        header_hex = utxo.get("header")
        if header_hex:
            header_bytes = bytes.fromhex(header_hex)
            if len(header_bytes) != 80:
                raise ValueError(f"Block header must be 80 bytes, got {len(header_bytes)}")
            data += header_bytes
        else:
            data += b"\x00" * 80

    return data

def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} input.json output.beef")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    with open(input_file, "r") as f:
        beef_json = json.load(f)

    binary_beef = json_to_binary_beef(beef_json)

    with open(output_file, "wb") as f:
        f.write(binary_beef)

    print(f"Binary BEEF file written to {output_file}")

if __name__ == "__main__":
    main()

