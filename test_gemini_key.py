import os
import requests
import json

api_key = "AIzaSyByb9sA6fKWMPg8_bgvhR6yA8dtJD9nEvI"
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

payload = {
    "contents": [{
        "parts": [{"text": "Hello, are you active?"}]
    }]
}

print(f"Testing Gemini API Key: {api_key[:10]}...")
try:
    response = requests.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
