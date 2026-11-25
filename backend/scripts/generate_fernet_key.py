#!/usr/bin/env python3
"""Generate a Fernet key for encrypting Binance API keys.
Usage: python scripts/generate_fernet_key.py
Put the output in .env as FERNET_KEY=<key>. Never commit a real key."""
from cryptography.fernet import Fernet

if __name__ == "__main__":
    print(Fernet.generate_key().decode())
