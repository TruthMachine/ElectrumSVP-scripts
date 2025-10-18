ElectrumSVP Test Scripts

This repository contains a collection of Python test scripts used during the development and design of ElectrumSVP. They cover blockchain header synchronization, UTXO extraction, BEEF generation, and proof verification.

Features

Header Sync & Subscribe

Downloads the full 74 MB headers file from genesis.

Subscribes to new headers as blocks are mined.

BEEF & Merkle Proof Extraction

Extracts BEEFs, Merkle proofs, UTXO data, and transaction information.

Verification Scripts

Verify proofs using block headers.

Parse and validate BEEF JSON files.

Multi-server Testing

Compare scripthash status and confirmed transactions across multiple ElectrumX servers.

Requirements

Python ≥ 3.7

Some scripts require BitcoinX

