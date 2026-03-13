import urllib.request
import json

try:
    url = "http://localhost:8000/api/portfolio"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        rebalancing = data.get('rebalancing', {})
        actions = rebalancing.get('actions', [])
        for a in actions:
            if 'GOOG' in a['ticker'] or 'NVO' in a['ticker'] or 'NOVO' in a['ticker']:
                print(f"Ticker: {a['ticker']}")
                print(f"  Action: {a['action']}")
                print(f"  Current: {a['current_weight']}% -> Target: {a['target_weight']}%")
                print(f"  Score: {a.get('score')} ({a.get('rating')})")
                print(f"  Conviction: {a.get('conviction')}")
                print(f"  Sector: {a.get('sector')}")
                print(f"  Reasons: {a.get('reasons')}")
                print("-" * 40)
except Exception as e:
    print(f"Error: {e}")
