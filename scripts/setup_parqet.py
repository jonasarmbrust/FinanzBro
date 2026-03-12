"""Parqet Setup - Token & Portfolio-ID Extraktion via Chrome-Session

Nutzt deine bestehende Chrome-Anmeldung bei Parqet, um:
1. Auth-Token aus dem /api/auth/tokens Endpoint abzufangen
2. Portfolio-IDs und Holdings-Daten zu finden
3. Alles in .env und Cache zu speichern

Danach kann FinanzBro die Parqet-API direkt nutzen - kein Developer-Account noetig.

Verwendung:
  python setup_parqet.py
"""
import asyncio
import io
import json
import logging
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
ENV_FILE = BASE_DIR / ".env"
CACHE_DIR = BASE_DIR / "cache"
TOKEN_FILE = CACHE_DIR / "parqet_tokens.json"
HOLDINGS_CACHE = CACHE_DIR / "parqet_holdings.json"

# Chrome user data directory
CHROME_USER_DATA = Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data"

load_dotenv(ENV_FILE)

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def update_env_file(key: str, value: str):
    """Setzt einen Wert in der .env Datei."""
    content = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    if pattern.search(content):
        content = pattern.sub(f"{key}={value}", content)
    else:
        content = content.rstrip() + f"\n{key}={value}\n"
    ENV_FILE.write_text(content, encoding="utf-8")


async def extract_parqet_credentials():
    """Oeffnet Parqet im Chrome-Browser und faengt Auth-Tokens + Holdings ab."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[X] Playwright nicht installiert.")
        print("    pip install playwright && playwright install chromium")
        sys.exit(1)

    if not CHROME_USER_DATA.exists():
        print(f"[X] Chrome User Data nicht gefunden: {CHROME_USER_DATA}")
        print("    Bitte stelle sicher, dass Google Chrome installiert ist.")
        sys.exit(1)

    print("=" * 60)
    print("  Parqet Setup - Token-Extraktion via Chrome")
    print("=" * 60)
    print(f"\n  Chrome-Profil: {CHROME_USER_DATA}")
    print("  WICHTIG: Chrome muss geschlossen sein!")

    # Copy Chrome user data to temp (Chrome locks the profile)
    temp_dir = Path(tempfile.mkdtemp(prefix="finanzbro_chrome_"))
    print(f"  Temp-Profil: {temp_dir}")

    try:
        # Copy only Default profile essentials
        default_src = CHROME_USER_DATA / "Default"
        default_dst = temp_dir / "Default"
        default_dst.mkdir()

        # Copy critical files for session persistence
        critical_files = [
            "Cookies", "Login Data", "Web Data",
            "Preferences", "Secure Preferences",
            "Local State",
        ]
        # Copy Local State from parent
        local_state = CHROME_USER_DATA / "Local State"
        if local_state.exists():
            shutil.copy2(local_state, temp_dir / "Local State")

        for fname in critical_files:
            src = default_src / fname
            if src.exists():
                shutil.copy2(src, default_dst / fname)

        # Copy local/session storage for auth tokens
        for dirname in ["Local Storage", "Session Storage", "IndexedDB"]:
            src = default_src / dirname
            if src.exists():
                shutil.copytree(src, default_dst / dirname, dirs_exist_ok=True)

    except PermissionError:
        print("\n[X] Chrome ist noch geoeffnet! Bitte Chrome schliessen und erneut starten.")
        shutil.rmtree(temp_dir, ignore_errors=True)
        sys.exit(1)
    except Exception as e:
        print(f"\n[X] Fehler beim Kopieren des Chrome-Profils: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        sys.exit(1)

    auth_tokens = set()
    portfolio_ids = set()
    holdings_data = []
    api_responses = []

    try:
        async with async_playwright() as p:
            # Launch Chromium with Chrome user data
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=str(temp_dir),
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--disable-gpu",
                ],
                viewport={"width": 1920, "height": 1080},
            )

            page = browser.pages[0] if browser.pages else await browser.new_page()

            async def capture_request(request):
                url = request.url
                headers = request.headers

                if "parqet" not in url:
                    return

                # Capture Bearer tokens
                auth_header = headers.get("authorization", "")
                if auth_header:
                    token = auth_header.replace("Bearer ", "").replace("bearer ", "")
                    if len(token) > 20:
                        auth_tokens.add(token)

            async def capture_response(response):
                url = response.url
                if "parqet" not in url or response.status != 200:
                    return

                try:
                    content_type = response.headers.get("content-type", "")
                    if "json" not in content_type:
                        return

                    body = await response.json()
                    api_responses.append({"url": url, "status": response.status})

                    # Capture auth tokens from the tokens endpoint
                    if "/api/auth/tokens" in url or "/auth/" in url:
                        if isinstance(body, dict):
                            for key in ["access_token", "accessToken", "token", "jwt"]:
                                if key in body and isinstance(body[key], str):
                                    auth_tokens.add(body[key])
                            # Supabase-style nested token
                            session = body.get("session", body.get("data", {}))
                            if isinstance(session, dict):
                                for key in ["access_token", "accessToken"]:
                                    if key in session:
                                        auth_tokens.add(session[key])

                    # Capture portfolio IDs
                    for pattern in [r'portfolioIds?[=/]([a-f0-9-]+)', r'/p/([a-f0-9]+)']:
                        for pid in re.findall(pattern, url):
                            if len(pid) > 8:
                                portfolio_ids.add(pid)

                    # Capture holdings data
                    if "/holdings" in url or "/portfolios/" in url:
                        if isinstance(body, (list, dict)):
                            holdings_data.append({"url": url, "data": body})

                    _extract_ids_from_data(body, portfolio_ids)

                except Exception:
                    pass

            page.on("request", capture_request)
            page.on("response", capture_response)

            # Step 1: Navigate to Parqet
            print("\n[1/3] Oeffne Parqet Dashboard...")
            try:
                await page.goto("https://app.parqet.com/", wait_until="networkidle", timeout=30000)
            except Exception:
                await page.goto("https://app.parqet.com/", timeout=30000)
            await page.wait_for_timeout(4000)

            current_url = page.url
            if "login" in current_url.lower() or "signin" in current_url.lower():
                print("[X] Nicht eingeloggt! Bitte zuerst in Chrome bei Parqet einloggen.")
                print("    1. Oeffne Chrome")
                print("    2. Gehe zu https://app.parqet.com und logge dich ein")
                print("    3. Schliesse Chrome")
                print("    4. Starte dieses Script erneut")
                await browser.close()
                shutil.rmtree(temp_dir, ignore_errors=True)
                sys.exit(1)

            print("[OK] Bei Parqet eingeloggt!")

            # Step 2: Navigate to portfolio to trigger API calls
            print("\n[2/3] Lade Portfolio-Daten...")

            for url in ["https://app.parqet.com/p", "https://app.parqet.com/portfolio"]:
                try:
                    await page.goto(url, wait_until="networkidle", timeout=20000)
                    await page.wait_for_timeout(3000)
                except Exception:
                    pass

            # Extract portfolio IDs from page
            for pattern in [r'/p/([a-f0-9]+)', r'portfolio[=/]([a-f0-9-]+)']:
                for pid in re.findall(pattern, page.url):
                    if len(pid) > 8:
                        portfolio_ids.add(pid)

            # Click portfolio links to load their data
            try:
                links = await page.query_selector_all('a[href*="/p/"]')
                for link in links[:5]:
                    href = await link.get_attribute("href")
                    if href:
                        for pid in re.findall(r'/p/([a-f0-9]+)', href):
                            if len(pid) > 8:
                                portfolio_ids.add(pid)
                        try:
                            await link.click()
                            await page.wait_for_timeout(3000)
                        except Exception:
                            pass
            except Exception:
                pass

            # Try page HTML for portfolio IDs
            try:
                html = await page.content()
                for pid in re.findall(r'["\'/]p/([a-f0-9]{10,})', html):
                    portfolio_ids.add(pid)
            except Exception:
                pass

            await browser.close()

    except Exception as e:
        print(f"\n[X] Browser-Fehler: {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    # ── Results ──
    print(f"\n[3/3] Ergebnisse:")
    print(f"  Auth-Tokens: {len(auth_tokens)}")
    print(f"  Portfolio-IDs: {len(portfolio_ids)}")
    print(f"  Holdings-Responses: {len(holdings_data)}")
    print(f"  API-Responses total: {len(api_responses)}")

    CACHE_DIR.mkdir(exist_ok=True)

    # Determine auth token
    auth_value = None
    if auth_tokens:
        auth_value = max(auth_tokens, key=len)
        print(f"\n  [OK] Auth-Token: {auth_value[:25]}...{auth_value[-10:]}")

    # Pick portfolio ID
    portfolio_id = ""
    if portfolio_ids:
        pids = list(portfolio_ids)
        if len(pids) == 1:
            portfolio_id = pids[0]
            print(f"  [OK] Portfolio-ID: {portfolio_id}")
        else:
            print(f"\n  Gefundene Portfolios ({len(pids)}):")
            for i, pid in enumerate(pids):
                print(f"    [{i+1}] {pid}")
            choice = input(f"  Welches Portfolio? [1-{len(pids)}, default=1]: ").strip()
            try:
                portfolio_id = pids[int(choice) - 1]
            except (ValueError, IndexError):
                portfolio_id = pids[0]
                print(f"  => Nehme: {portfolio_id}")

    # ── Save ──
    print("\n" + "-" * 60)

    if auth_value:
        update_env_file("PARQET_ACCESS_TOKEN", auth_value)
        print(f"  [OK] PARQET_ACCESS_TOKEN in .env gespeichert")

    if portfolio_id:
        update_env_file("PARQET_PORTFOLIO_ID", portfolio_id)
        print(f"  [OK] PARQET_PORTFOLIO_ID={portfolio_id}")

    # Save holdings data for immediate use
    if holdings_data:
        HOLDINGS_CACHE.write_text(
            json.dumps(holdings_data, indent=2, default=str), encoding="utf-8"
        )
        print(f"  [OK] Holdings-Daten zwischengespeichert ({len(holdings_data)} Responses)")

    # Save token cache
    TOKEN_FILE.write_text(json.dumps({
        "access_token": auth_value or "",
        "portfolio_ids": list(portfolio_ids),
        "updated_at": datetime.now().isoformat(),
    }, indent=2), encoding="utf-8")

    # ── Quick API test ──
    if auth_value:
        print("\n  Teste API-Zugriff...")
        try:
            import httpx
            headers = {"Authorization": f"Bearer {auth_value}"}
            resp = httpx.get(
                f"https://api.parqet.com/v1/holdings?portfolioIds={portfolio_id}",
                headers=headers, timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                count = len(data) if isinstance(data, list) else "?"
                print(f"  [OK] API funktioniert! ({count} Holdings)")
            else:
                print(f"  [!] API-Status {resp.status_code}")
        except Exception as e:
            print(f"  [!] API-Test: {e}")

    if not auth_value and not portfolio_id:
        print("\n  [!] Weder Token noch Portfolio-ID gefunden.")
        print("      Bist du in Chrome bei Parqet eingeloggt?")
        print("      1. Chrome oeffnen, bei parqet.com einloggen")
        print("      2. Chrome SCHLIESSEN")
        print("      3. Dieses Script erneut starten")

    print()
    print("=" * 60)
    print("  Setup abgeschlossen! Starte FinanzBro mit: python main.py")
    print("=" * 60)


def _extract_ids_from_data(data, portfolio_ids: set):
    """Extrahiert Portfolio-IDs aus API-Antworten."""
    if isinstance(data, dict):
        for key in ["_id", "id", "portfolioId"]:
            val = data.get(key)
            if isinstance(val, str) and len(val) > 8 and re.match(r'^[a-f0-9-]+$', val):
                portfolio_ids.add(val)
        for val in data.values():
            if isinstance(val, (dict, list)):
                _extract_ids_from_data(val, portfolio_ids)
    elif isinstance(data, list):
        for item in data[:50]:
            if isinstance(item, (dict, list)):
                _extract_ids_from_data(item, portfolio_ids)


if __name__ == "__main__":
    asyncio.run(extract_parqet_credentials())
