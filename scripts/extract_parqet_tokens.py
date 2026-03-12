"""Extracts fresh Parqet tokens from Firefox cookies.

Saves both access and refresh tokens to cache/parqet_tokens.json.
Run this before deploying to ensure Cloud Run gets fresh tokens.

Usage: python scripts/extract_parqet_tokens.py
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fetchers.parqet_auth import refresh_token_from_firefox, load_token_file, is_token_expired


def main():
    print("🔑 Extrahiere Parqet-Tokens aus Firefox...")
    token = refresh_token_from_firefox()

    if not token:
        print("❌ Kein gültiger Token in Firefox gefunden!")
        print("   → Bitte auf https://app.parqet.com einloggen und erneut versuchen.")
        sys.exit(1)

    stored = load_token_file()
    refresh = stored.get("refresh_token", "") if stored else ""

    print(f"✅ Access Token: OK (Länge={len(token)})")
    print(f"✅ Refresh Token: {refresh[:8]}..." if refresh else "⚠️  Kein Refresh Token")
    print(f"✅ Abgelaufen: {is_token_expired(token)}")
    print(f"✅ Gespeichert in cache/parqet_tokens.json")


if __name__ == "__main__":
    main()
