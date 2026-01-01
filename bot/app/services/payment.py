import midtransclient
from flask import request
from app.config import Config
import logging
import uuid

# Initialize Snap API Client
snap = midtransclient.Snap(
    is_production=Config.MIDTRANS_IS_PRODUCTION,
    server_key=Config.MIDTRANS_SERVER_KEY,
    client_key=Config.MIDTRANS_CLIENT_KEY
)

def create_payment_link(details):
    """
    Create Payment Link via Midtrans Snap.
    details = {
        'order_id': 'SUBS-12345',
        'amount': 99000,
        'customer_details': {
            'first_name': 'Toko Kopi',
            'phone': '08123456789'
        },
        'item_details': [{
            'id': 'STARTER',
            'price': 99000,
            'quantity': 1,
            'name': 'Starter Plan 1 Month'
        }]
    }
    """
    try:
        param = {
            "transaction_details": {
                "order_id": details['order_id'],
                "gross_amount": details['amount']
            },
            "credit_card": {
                "secure": True
            },
            "customer_details": details.get('customer_details'),
            "item_details": details.get('item_details'),
            "callbacks": {
                "finish": f"https://saas-bot-643221888510.asia-southeast2.run.app/success?order_id={details['order_id']}",
                "unfinish": f"https://saas-bot-643221888510.asia-southeast2.run.app/subscribe",
                "error": f"https://saas-bot-643221888510.asia-southeast2.run.app/subscribe"
            },

            "expiry": {
                "duration": 24,
                "unit": "hours"
            }
        }

        
        logging.info(f"Creating Midtrans Link for {details['order_id']}")
        transaction = snap.create_transaction(param)
        return transaction['redirect_url']
        
    except Exception as e:
        logging.error(f"Midtrans Error: {e}")
        return None
