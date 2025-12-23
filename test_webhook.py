import requests
import json

# Simulate a webhook POST from WAHA to Bot
webhook_url = "http://localhost:5000/webhook"

# Test payload mimicking a /daftar command
payload = {
    "event": "message",
    "session": "default",
    "payload": {
        "id": "test_msg_123",
        "timestamp": 1703350800,
        "from": "628123456789@c.us",
        "fromMe": False,
        "body": "/daftar TokoTest #Premium",
        "hasMedia": False,
        "ack": 1,
        "chatId": "628123456789@c.us"
    }
}

print("--- Simulating Webhook POST ---")
print(f"Target: {webhook_url}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print("\nSending...")

try:
    response = requests.post(webhook_url, json=payload, timeout=10)
    print(f"\n✅ Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("\n🎉 BOT LOGIC WORKS! The issue is WAHA not sending webhooks.")
    else:
        print(f"\n❌ Bot returned error: {response.status_code}")
except Exception as e:
    print(f"\n❌ Connection Error: {e}")
