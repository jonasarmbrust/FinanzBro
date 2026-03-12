"""Deploys FinanzBro to Cloud Run with fresh Parqet tokens.

Reads tokens from cache/parqet_tokens.json and .env,
then runs gcloud run deploy with all required env vars.

Usage: python scripts/deploy_cloud_run.py
"""
import json
import os
import subprocess
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import dotenv_values


def main():
    # Load .env
    env = dotenv_values(ROOT / ".env")

    # Load fresh tokens from cache
    token_file = ROOT / "cache" / "parqet_tokens.json"
    if token_file.exists():
        tokens = json.loads(token_file.read_text(encoding="utf-8"))
        access_token = tokens.get("access_token", "")
        refresh_token = tokens.get("refresh_token", "")
        print(f"📦 Tokens aus Cache geladen (updated: {tokens.get('updated_at', '?')})")
    else:
        access_token = env.get("PARQET_ACCESS_TOKEN", "")
        refresh_token = env.get("PARQET_REFRESH_TOKEN", "")
        print("⚠️  Kein Token-Cache, verwende .env Tokens")

    if not access_token:
        print("❌ Kein Parqet Access Token! Bitte erst:")
        print("   python scripts/extract_parqet_tokens.py")
        sys.exit(1)

    # Build env vars for Cloud Run
    cloud_env = {
        "ENVIRONMENT": "production",
        "GCP_PROJECT_ID": "job-automation-jonas",
        "FMP_API_KEY": env.get("FMP_API_KEY", ""),
        "PARQET_ACCESS_TOKEN": access_token,
        "PARQET_REFRESH_TOKEN": refresh_token,
        "PARQET_PORTFOLIO_ID": env.get("PARQET_PORTFOLIO_ID", ""),
        "TELEGRAM_BOT_TOKEN": env.get("TELEGRAM_BOT_TOKEN", ""),
        "TELEGRAM_CHAT_ID": env.get("TELEGRAM_CHAT_ID", ""),
        "GEMINI_API_KEY": env.get("GEMINI_API_KEY", ""),
        "FINNHUB_API_KEY": env.get("FINNHUB_API_KEY", ""),
        "DAILY_REFRESH_TIME": env.get("DAILY_REFRESH_TIME", "06:00"),
        "PRICE_UPDATE_INTERVAL_MIN": env.get("PRICE_UPDATE_INTERVAL_MIN", "30"),
        "AI_AGENT_TIME": env.get("AI_AGENT_TIME", "15:50"),
    }

    # Build gcloud command with separate --set-env-vars for each
    # (avoids issues with JWTs containing special characters)
    cmd = [
        "gcloud", "run", "deploy", "finanzbro",
        f"--source={ROOT}",
        "--region=europe-west1",
        "--allow-unauthenticated",
        "--memory=512Mi",
        "--cpu=1",
        "--min-instances=0",
        "--max-instances=1",
        "--timeout=300",
        "--quiet",
    ]
    for key, value in cloud_env.items():
        if value:
            cmd.append(f"--set-env-vars={key}={value}")

    print(f"\n🚀 Deploying to Cloud Run...")
    print(f"   Region: europe-west1")
    print(f"   Positionen: PARQET_PORTFOLIO_ID={cloud_env['PARQET_PORTFOLIO_ID'][:8]}...")
    print(f"   Token: {access_token[:30]}...")
    print()

    result = subprocess.run(cmd, cwd=str(ROOT))
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
