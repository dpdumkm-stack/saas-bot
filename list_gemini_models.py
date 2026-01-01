import os
import requests

api_key = "AIzaSyByb9sA6fKWMPg8_bgvhR6yA8dtJD9nEvI"
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

print(f"Listing models for key: {api_key[:10]}...")
try:
    response = requests.get(url, timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✓ API Key is VALID")
    else:
        print(f"✗ API Key result: {response.text}")
except Exception as e:
    print(f"Error: {e}")
