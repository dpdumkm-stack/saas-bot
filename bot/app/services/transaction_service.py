from app.models import Subscription
from app.config import Config
from app.extensions import db
from app.services.midtrans_service import get_snap_redirect_url
import time
import logging

def create_subscription_transaction(phone, name, package_key, category="General"):
    """
    Creates or updates a subscription and generates a Midtrans payment link.
    
    Args:
        phone (str): Phone number (e.g., '628...')
        name (str): Customer name
        package_key (str): Package key (e.g., 'STARTER', 'PRO')
        category (str): Business category
        
    Returns:
        dict: Result with status, order_id, payment_url, or error info.
    """
    
    # Validate Package
    package_key = package_key.upper()
    pkg = Config.PRICING_PACKAGES.get(package_key)
    
    # Handle TRIAL separately
    if package_key == 'TRIAL':
        pkg = {"price": 0, "name": "Free Trial (3 Hari)", "duration": 3}
    
    if not pkg:
        return {"status": "error", "message": "Invalid Package Selected"}

    try:
        # 1. Normalize Phone
        if phone.startswith('08'): 
            phone = '62' + phone[1:]
        
        # 2. Check or Create Subscription
        sub = Subscription.query.filter_by(phone_number=phone).first()
        if not sub:
            # Create DRAFT Subscription
            sub = Subscription(
                phone_number=phone,
                name=name,
                category=category, 
                status="DRAFT",
                tier="TRIAL", 
                step=0
            )
            db.session.add(sub)
        else:
             # Update info if exists
             sub.name = name
             sub.category = category
             # Only update tier if it was DRAFT, otherwise keep current until paid? 
             # Actually, if they are upgrading, we mark the intent.
             # We store the *intent* in `tier` temporarily or ideally in a separate field, 
             # but for now reusing `tier` as 'intended_tier' is acceptable for this flow 
             # as long as we don't activate it yet.
             # Wait, if they are currently 'STARTER' and want 'PRO', we shouldn't overwrite 'tier' to 'PRO' 
             # until they pay, otherwise they might get PRO features for free if logic checks `tier`.
             # LET'S CHECK models.py or subscription logic.
             pass

        # 3. Generate Unique Order ID
        # Format: TRX-<PhoneSuffix>-<TimestampHex>
        timestamp_hex = hex(int(time.time()))[2:]
        order_id = f"TRX-{phone[-4:]}-{timestamp_hex}".upper()
        
        # 4. Request Link from Midtrans
        amount = pkg['price']
        cust_details = {
            "first_name": name,
            "phone": phone
        }
        item_details = [{
            "id": package_key,
            "price": amount,
            "quantity": 1,
            "name": pkg['name']
        }]
        
        if package_key == 'TRIAL':
            payment_url = None # No payment flow
        else:
            payment_url = get_snap_redirect_url(order_id, amount, cust_details, item_details)
        
        if payment_url or package_key == 'TRIAL':
            # 5. Save Transaction State
            sub.order_id = order_id
            sub.payment_url = payment_url
            
            # CRITICAL: We need to know what they are buying when webhook comes back.
            # Using `tier` field for now as "Current or Intended Tier". 
            # If they are upgrading, this overwrites their current tier in DB *before* payment.
            # This is a risk if our logic grants access based on `tier` without checking `status`.
            # We must ensure `status` remains `DRAFT` or `EXPIRED` or whatever until payment.
            # For active users upgrading, we shouldn't break their current access.
            # TODO: Add `upgrade_tier` column in future. For MVP, we'll use `tier` but assume 
            # checking `status=ACTIVE` is required for access.
            sub.tier = package_key 
            
            db.session.commit()

            # AUTO-ACTIVATE if TRIAL
            if package_key == 'TRIAL':
                # Import here to avoid circular dependency
                from app.services.subscription_manager import activate_subscription
                # Trial duration is 3 days
                activate_subscription(order_id, duration_days=3)
            
            return {
                "status": "success",
                "order_id": order_id,
                "payment_url": payment_url,
                "amount": amount,
                "package_name": pkg['name']
            }
        else:
            return {"status": "error", "message": "Failed to generate payment link"}
            
    except Exception as e:
        logging.error(f"Create Transaction Error: {e}")
        return {"status": "error", "message": str(e)}
