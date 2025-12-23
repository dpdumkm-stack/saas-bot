import requests

WAHA_BASE_URL = "http://waha:3000"
API_KEY = "abc123secretkeyQM8"
SESSION = "default"

endpoints = [
    f"/api/sessions/{SESSION}/messages",
    f"/api/{SESSION}/messages",
    f"/api/default/messages",
    "/api/messages",
    f"/api/sessions/{SESSION}/chats",
    f"/api/{SESSION}/chats",
    "/api/chats",
    f"/api/sessions/{SESSION}/history",
    "/api/history",
    f"/api/sessions/{SESSION}/all-messages",
    "/api/sessions"
]

headers = {"X-Api-Key": API_KEY}

print("--- Probing WAHA Endpoints ---")
found = False
for path in endpoints:
    url = f"{WAHA_BASE_URL}{path}"
    try:
        # Try GET with query params often used
        r = requests.get(f"{url}?limit=5", headers=headers, timeout=2)
        print(f"[{r.status_code}] {path}")
        if r.status_code == 200:
            print(f"   >>> FOUND! Response keys: {list(r.json().keys()) if isinstance(r.json(), dict) else 'List'}")
            found = True
    except Exception as e:
        print(f"[ERR] {path}: {e}")

if not found:
    print("--- No standard endpoints found. Checking /api-docs/json again... ---")
