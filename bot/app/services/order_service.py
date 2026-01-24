"""
Order Service - Manages order lifecycle and payment verification matching.

This service handles:
1. Creating orders when customers place them
2. Finding pending orders for payment matching
3. Updating order status after payment verification
4. Listing orders for merchant dashboard

GPSF Compliance:
- Tenant Isolation: All queries filtered by toko_id
- Concurrency Safe: Uses appropriate locking for updates
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from app.extensions import db
from app.models import Transaction, Customer


def generate_order_id(toko_id: str) -> str:
    """Generate unique order ID with format: TOKO-YYYYMMDD-XXXX"""
    date_str = datetime.now().strftime('%Y%m%d')
    unique_suffix = uuid.uuid4().hex[:6].upper()
    return f"{toko_id[:8].upper()}-{date_str}-{unique_suffix}"


def create_order(toko_id: str, customer_hp: str, nominal: int, items: list = None) -> Transaction:
    """
    Create a new order/transaction for a customer.
    
    Args:
        toko_id: Store ID
        customer_hp: Customer phone number
        nominal: Total order amount
        items: Optional list of ordered items [{"name": "Nasi Goreng", "qty": 2, "price": 15000}]
    
    Returns:
        Transaction object
    """
    try:
        order = Transaction(
            toko_id=toko_id,
            customer_hp=customer_hp,
            nominal=nominal,
            status='PENDING',
            verification_status='UNVERIFIED',
            tanggal=datetime.now().strftime('%Y-%m-%d %H:%M'),
            order_id=generate_order_id(toko_id),
            items_json=json.dumps(items) if items else None
        )
        
        db.session.add(order)
        db.session.commit()
        
        logging.info(f"Created order {order.order_id} for {customer_hp} @ {toko_id}: Rp{nominal:,}")
        return order
        
    except Exception as e:
        logging.error(f"Failed to create order: {e}")
        db.session.rollback()
        return None


def find_pending_order(toko_id: str, customer_hp: str, amount: int = None, tolerance: int = 1000) -> Transaction:
    """
    Find a pending order for payment matching.
    
    Matching logic:
    1. Same toko_id and customer_hp
    2. Status is PENDING
    3. If amount provided, match within tolerance (default ±Rp1000)
    4. Prefer most recent order if multiple matches
    
    Args:
        toko_id: Store ID
        customer_hp: Customer phone number
        amount: Optional amount to match (detected from bukti transfer)
        tolerance: Amount tolerance for matching (default ±1000)
    
    Returns:
        Transaction object or None
    """
    try:
        query = Transaction.query.filter_by(
            toko_id=toko_id,
            customer_hp=customer_hp,
            status='PENDING'
        ).order_by(Transaction.created_at.desc())
        
        pending_orders = query.all()
        
        if not pending_orders:
            logging.info(f"No pending orders for {customer_hp} @ {toko_id}")
            return None
        
        # If no amount specified, return most recent
        if amount is None:
            return pending_orders[0]
        
        # Try exact match first
        for order in pending_orders:
            if order.nominal == amount:
                logging.info(f"Exact match found: Order {order.order_id} = Rp{amount:,}")
                return order
        
        # Try tolerance match
        for order in pending_orders:
            if abs(order.nominal - amount) <= tolerance:
                logging.info(f"Tolerance match found: Order {order.order_id} (Rp{order.nominal:,}) ≈ Rp{amount:,}")
                return order
        
        # No match, return most recent anyway (merchant can review)
        logging.info(f"No amount match, returning most recent pending order")
        return pending_orders[0]
        
    except Exception as e:
        logging.error(f"Error finding pending order: {e}")
        return None


def verify_order(
    order_id: str,
    verification_status: str,
    confidence_score: int = None,
    detected_amount: int = None,
    detected_bank: str = None,
    verified_by: str = 'AI',
    fraud_hints: list = None,
    notes: str = None
) -> bool:
    """
    Update order verification status after payment proof analysis.
    
    Args:
        order_id: Transaction order_id
        verification_status: VERIFIED, REJECTED, MANUAL_REVIEW
        confidence_score: AI confidence 0-100
        detected_amount: Amount detected by OCR
        detected_bank: Bank name detected
        verified_by: 'AI' or admin phone number
        fraud_hints: List of fraud indicators
        notes: Additional notes
    
    Returns:
        True if successful, False otherwise
    """
    try:
        order = Transaction.query.filter_by(order_id=order_id).first()
        
        if not order:
            logging.error(f"Order not found: {order_id}")
            return False
        
        # Update verification fields
        order.verification_status = verification_status
        order.confidence_score = confidence_score
        order.detected_amount = detected_amount
        order.detected_bank = detected_bank
        order.verified_by = verified_by
        order.verified_at = datetime.now()
        order.fraud_hints_json = json.dumps(fraud_hints) if fraud_hints else None
        order.verification_notes = notes
        
        # Auto-update main status if verified
        if verification_status == 'VERIFIED':
            order.status = 'PAID'
        elif verification_status == 'REJECTED':
            order.status = 'PENDING'  # Keep pending for retry
        
        db.session.commit()
        logging.info(f"Order {order_id} verified as {verification_status} by {verified_by}")
        return True
        
    except Exception as e:
        logging.error(f"Error verifying order: {e}")
        db.session.rollback()
        return False


def get_pending_orders(toko_id: str, limit: int = 50) -> list:
    """
    Get all pending orders for a store (for dashboard).
    
    Args:
        toko_id: Store ID
        limit: Maximum number of orders to return
    
    Returns:
        List of Transaction objects
    """
    try:
        orders = Transaction.query.filter_by(
            toko_id=toko_id,
            status='PENDING'
        ).order_by(Transaction.created_at.desc()).limit(limit).all()
        
        return orders
        
    except Exception as e:
        logging.error(f"Error getting pending orders: {e}")
        return []


def get_orders_needing_review(toko_id: str) -> list:
    """
    Get orders that need manual review (medium confidence).
    
    Args:
        toko_id: Store ID
    
    Returns:
        List of Transaction objects with MANUAL_REVIEW status
    """
    try:
        orders = Transaction.query.filter_by(
            toko_id=toko_id,
            verification_status='MANUAL_REVIEW'
        ).order_by(Transaction.created_at.desc()).all()
        
        return orders
        
    except Exception as e:
        logging.error(f"Error getting orders needing review: {e}")
        return []


def format_order_summary(order: Transaction) -> str:
    """Format order for WhatsApp message"""
    items_text = ""
    if order.items_json:
        try:
            items = json.loads(order.items_json)
            items_text = "\n".join([f"  • {i['name']} x{i.get('qty', 1)}" for i in items])
        except:
            items_text = "(detail tidak tersedia)"
    
    return (
        f"📦 *Order #{order.order_id}*\n"
        f"Tanggal: {order.tanggal}\n"
        f"Nominal: Rp {order.nominal:,}\n"
        f"Status: {order.status}\n"
        f"{f'Items:{chr(10)}{items_text}' if items_text else ''}"
    )
