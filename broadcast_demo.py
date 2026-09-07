import json
import socket
import ssl
import sys

# ElectrumX server
HOST = "electrumx.gorillapool.io"
PORT = 50002  # SSL

def broadcast_transaction(raw_tx_hex):
    request = {
        "id": 1,
        "method": "blockchain.transaction.broadcast",
        "params": [raw_tx_hex],
    }

    message = json.dumps(request) + "\n"

    print()
    print("=" * 60)
    print("STEP 1: CONNECTING TO ELECTRUMX")
    print("=" * 60)
    print(f"Server: {HOST}:{PORT}")

    sock = socket.create_connection((HOST, PORT), timeout=15)

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    sock = context.wrap_socket(sock, server_hostname=HOST)

    try:
        print("✓ Connected successfully")
        print()
        print("=" * 60)
        print("STEP 2: BROADCASTING TRANSACTION")
        print("=" * 60)
        print(f"Transaction size: {len(raw_tx_hex) // 2} bytes")
        print()
        print("Sending:")
        print(message)

        sock.sendall(message.encode("utf-8"))

        response = b""

        while b"\n" not in response:
            chunk = sock.recv(4096)

            if not chunk:
                break

            response += chunk

        response_text = response.decode("utf-8")

        print()
        print("=" * 60)
        print("STEP 3: ELECTRUMX RESPONSE")
        print("=" * 60)
        print(response_text)

        result = json.loads(response_text)

        print()

        if "result" in result and result["result"]:
            txid = result["result"]

            print("=" * 60)
            print("              BROADCAST SUCCESSFUL")
            print("=" * 60)
            print()
            print("ElectrumX accepted the transaction.")
            print()
            print(f"TXID:")
            print(txid)
            print()
            print("The transaction was submitted to the")
            print("Bitcoin network through the ElectrumX server.")
            print()
            print("=" * 60)

        elif "error" in result:
            print("=" * 60)
            print("              BROADCAST REJECTED")
            print("=" * 60)
            print()
            print(result["error"])
            print()
            print("=" * 60)

    finally:
        sock.close()


if __name__ == "__main__":
    print("ElectrumX Transaction Broadcast Demo")
    print("-------------------------------------")
    print()

    raw_tx = input("Paste raw signed transaction hex: ").strip()

    if not raw_tx:
        print("No transaction supplied.")
        sys.exit(1)

    broadcast_transaction(raw_tx)
