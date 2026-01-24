from datetime import datetime, timedelta
import logging

class MockCustomer:
    def __init__(self, msg=None, at=None, count=0):
        self.nomor_hp = "628123456"
        self.last_broadcast_msg = msg
        self.last_broadcast_at = at
        self.broadcast_reply_count = count

def simulate_gemini_logic(user_input, customer):
    # SIMULATED LOGIC FROM gemini.py (v3.9.7)
    broadcast_context = ""
    if customer.last_broadcast_msg and customer.last_broadcast_at:
        time_diff = datetime.utcnow() - customer.last_broadcast_at
        if time_diff.total_seconds() < 86400: # 24 hours
            if customer.broadcast_reply_count >= 2:
                return "[BLOCKED BY SAFETY FUSE]"
            
            broadcast_context = f"\n\n[KONTEKS BROADCAST]:\nAnda baru saja mengirim: \"{customer.last_broadcast_msg}\"\nPrioritaskan ini jika ambigu."
            customer.broadcast_reply_count += 1
    
    prompt = f"System: Asisten Toko.{broadcast_context}\nUser: {user_input}"
    return f"AI Response (Prompt: {prompt})"

# Test Case 1: Active Broadcast Context
print("--- TEST 1: Recent Broadcast ---")
cust = MockCustomer(msg="Promo Bakso 50%", at=datetime.utcnow() - timedelta(minutes=10))
res = simulate_gemini_logic("Mau dong kak", cust)
print(f"Result: {res}")
print(f"Reply Count: {cust.broadcast_reply_count}")

# Test Case 2: Safety Fuse Trigger
print("\n--- TEST 2: Safety Fuse Trigger ---")
cust.broadcast_reply_count = 2
res = simulate_gemini_logic("Mau dong kak", cust)
print(f"Result: {res}")

# Test Case 3: Expired Context (>24h)
print("\n--- TEST 3: Expired Context ---")
cust = MockCustomer(msg="Promo Kemarin", at=datetime.utcnow() - timedelta(hours=25))
res = simulate_gemini_logic("Halo", cust)
print(f"Result: {res}")
if "[KONTEKS BROADCAST]" not in res:
    print("PASS: Context ignored correctly after 24h")
