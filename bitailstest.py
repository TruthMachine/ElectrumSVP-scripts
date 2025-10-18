#!/usr/bin/env python3
import asyncio
import ssl
import logging
from aiorpcx import connect_rs

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

SERVERS = [
    ("esv.bitails.io", 50002),
    ("electrum.gorillapool.io", 50002),
    ("sv.satoshi.io", 50002)
]

TEST_SCRIPTHASHES = [
    "64c03511d7590feb15f325c8f765fc99c1481dde205f14a8b2a60be595d5cf6a"
]

# SSL context that allows self-signed certs
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

async def fetch_server_version(client, host, port):
    try:
        version = await client.send_request("server.version", ["testclient", "1.4"])
        logging.info(f"{host}:{port} reports version: {version}")
        return version
    except Exception as e:
        logging.error(f"{host}:{port} failed to report version: {e}")
        return None

async def fetch_blockchain_tip(client, host, port):
    try:
        tip = await client.send_request("blockchain.headers.subscribe", [])
        logging.info(f"{host}:{port} tip height: {tip['height']}, hex: {tip['hex'][:16]}…")
        return tip
    except Exception as e:
        logging.error(f"{host}:{port} failed to fetch blockchain tip: {e}")
        return None

async def fetch_scripthash(client, sh, host, port):
    try:
        res = await client.send_request("blockchain.scripthash.subscribe", [sh])
        # Normalize Bitails-style responses: hex:height -> hex
        if res and ":" in res:
            res = res.split(":")[0]
        logging.info(f"{host}:{port} -> {sh}: {res}")
        return res
    except Exception as e:
        logging.error(f"{host}:{port} -> Error subscribing to {sh}: {e}")
        return None

async def fetch_confirmed_history(client, sh, host, port):
    try:
        history = await client.send_request("blockchain.scripthash.get_history", [sh])
        logging.info(f"{host}:{port} -> confirmed txs: {len(history)}")
        return history
    except Exception as e:
        logging.error(f"{host}:{port} -> Error fetching history for {sh}: {e}")
        return None

async def test_server(host, port):
    server_name = f"{host}:{port}"
    try:
        async with connect_rs(host, port, ssl=ssl_context) as client:
            logging.info(f"Connected to {server_name}")
            version = await fetch_server_version(client, host, port)
            tip = await fetch_blockchain_tip(client, host, port)
            scripthash_results = {}
            history_results = {}
            for sh in TEST_SCRIPTHASHES:
                scripthash_results[sh] = await fetch_scripthash(client, sh, host, port)
                history_results[sh] = await fetch_confirmed_history(client, sh, host, port)
            return server_name, version, tip, scripthash_results, history_results
    except Exception as e:
        logging.error(f"Failed to connect to {server_name} - {e}")
        return server_name, None, None, {sh: None for sh in TEST_SCRIPTHASHES}, {sh: None for sh in TEST_SCRIPTHASHES}

async def main():
    tasks = [test_server(host, port) for host, port in SERVERS]
    all_results = await asyncio.gather(*tasks)

    for sh in TEST_SCRIPTHASHES:
        logging.info(f"=== Comparing results for scripthash {sh} ===")
        scripthash_seen = {}
        tip_heights = {}
        confirmed_histories = {}
        for server_name, version, tip, s_results, h_results in all_results:
            scripthash_seen[server_name] = s_results.get(sh)
            tip_heights[server_name] = tip['height'] if tip else None
            confirmed_histories[server_name] = h_results.get(sh) if h_results else None

        # Log tip heights
        logging.info("--- Server tips ---")
        for server, h in tip_heights.items():
            logging.info(f"{server}: {h}")

        # Compare scripthash subscribe values
        unique_scripthash_values = set(scripthash_seen.values())
        if len(unique_scripthash_values) == 1:
            logging.info(f"All servers agree on scripthash status: {unique_scripthash_values.pop()}")
        else:
            logging.warning("Servers disagree on scripthash status:")
            for server, val in scripthash_seen.items():
                logging.warning(f"  {server}: {val}")

        # Compare confirmed tx counts
        logging.info("--- Confirmed transaction counts ---")
        for server, hist in confirmed_histories.items():
            count = len(hist) if hist else None
            logging.info(f"{server}: {count} confirmed txs")

        # Optional: Compare txids
        logging.info("--- Confirmed transaction txids ---")
        for server, hist in confirmed_histories.items():
            if hist:
                txids = [entry['tx_hash'] for entry in hist]
                logging.info(f"{server}: {txids}")
            else:
                logging.info(f"{server}: None")

if __name__ == "__main__":
    asyncio.run(main())

