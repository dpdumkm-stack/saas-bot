import base64
import requests
import logging
from app.config import Config

# Midtrans Configuration
IS_PRODUCTION = Config.MIDTRANS_IS_PRODUCTION
SERVER_KEY = Config.MIDTRANS_SERVER_KEY

if IS_PRODUCTION:
    BASE_URL = "https://app.midtrans.com/snap/v1/transactions"
else:
    BASE_URL = "https://app.sandbox.midtrans.com/snap/v1/transactions"

def get_snap_redirect_url(order_id, amount, customer_details=None, item_details=None):
    """
    Generate SNAP Redirect URL for a transaction.
    
    Args:
        order_id (str): Unique Order ID.
        amount (int): Amount in IDR.
        customer_details (dict): { "first_name": "...", "email": "...", "phone": "..." }
        item_details (list): [ { "id": "...", "price": 1000, "quantity": 1, "name": "..." } ]
        
    Returns:
        str: Redirect URL or None if failed.
    """
    if not SERVER_KEY:
        logging.error("❌ MIDTRANS_SERVER_KEY is missing!")
        return None
        
    # Create Auth Header
    auth_string = f"{SERVER_KEY}:"
    auth_bytes = auth_string.encode('ascii')
    base64_bytes = base64.b64encode(auth_bytes)
    auth_header = f"Basic {base64_bytes.decode('ascii')}"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": auth_header
    }
    
    payload = {
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": int(amount)
        },
        "credit_card": {
            "secure": True
        }
    }
    
    if customer_details:
        payload["customer_details"] = customer_details
        
    if item_details:
        payload["item_details"] = item_details
        
    # Transaction callbacks (redirect user back to our site)
    # We can set this in SNAP Dashboard, or override here if SNAP allows (usually Dashboard settings prevail for redirect)
    
    try:
        logging.info(f"Generating Payment Link for {order_id} (Rp {amount})...")
        response = requests.post(BASE_URL, json=payload, headers=headers, timeout=10)
        
        if response.status_code in [200, 201]:
            data = response.json()
            redirect_url = data.get("redirect_url")
            logging.info(f"✅ Payment Link Generated: {redirect_url}")
            return redirect_url
        else:
            logging.error(f"❌ Midtrans Error ({response.status_code}): {response.text}")
            return None
            
    except Exception as e:
        logging.error(f"❌ Connection Error to Midtrans: {e}")
        return None
