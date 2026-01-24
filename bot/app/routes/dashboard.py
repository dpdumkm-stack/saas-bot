from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from app.models import Toko, ChatLog, Customer, Transaction, SystemConfig
from app.config import Config
from app.extensions import db
from datetime import datetime, timedelta
import functools

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'toko_id' not in session:
            return redirect(url_for('dashboard.login'))
        
        # Check subscription status - block inactive subscriptions
        from app.models import Subscription
        sub = Subscription.query.filter_by(phone_number=session['toko_id']).first()
        
        if not sub or sub.status in ['CANCELLED', 'EXPIRED']:
            # Redirect to inactive subscription page
            return redirect(url_for('dashboard.subscription_inactive'))
        
        return f(*args, **kwargs)
    return decorated_function

@dashboard_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Normalize Phone Number (Supports 08.., 62.., +62..)
        from app.utils import normalize_phone_number
        phone = normalize_phone_number(request.form.get('phone'))
        
        pin = request.form.get('pin')
        
        # Simple Logic: Check Toko ID & Remote PIN
        toko = Toko.query.get(phone)
        if toko and toko.remote_pin == pin:
            session['toko_id'] = toko.id
            return redirect(url_for('dashboard.index'))
        else:
            return render_template('dashboard/login.html', error="Login Gagal. Cek HP & PIN.")
            
    return render_template('dashboard/login.html')

@dashboard_bp.route('/logout')
def logout():
    session.pop('toko_id', None)
    return redirect(url_for('dashboard.login'))

@dashboard_bp.route('/connect')
@login_required
def connect_whatsapp():
    """Helper route to redirect to the correct success/QR page for the current user"""
    from app.models import Subscription
    toko_id = session['toko_id']
    sub = Subscription.query.filter_by(phone_number=toko_id).first()
    
    if sub and sub.order_id:
        return redirect(url_for('admin.success_page', order_id=sub.order_id))
    else:
        # Fallback if no order_id (shouldn't happen for valid users)
        return redirect(url_for('dashboard.index'))

# --- Product Management Routes ---

@dashboard_bp.route('/products')
@login_required
def products():
    toko = Toko.query.get(session['toko_id'])
    from app.services.product_service import get_products
    products = get_products(toko.id)
    return render_template('dashboard/products.html', toko=toko, products=products)

@dashboard_bp.route('/products/add', methods=['POST'])
@login_required
def add_product_route():
    from app.services.product_service import add_product
    data = request.form.to_dict()
    result = add_product(session['toko_id'], data)
    return jsonify(result)

@dashboard_bp.route('/products/edit/<int:product_id>', methods=['POST'])
@login_required
def edit_product_route(product_id):
    from app.services.product_service import update_product
    data = request.form.to_dict()
    result = update_product(product_id, session['toko_id'], data)
    return jsonify(result)

@dashboard_bp.route('/products/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product_route(product_id):
    from app.services.product_service import delete_product
    result = delete_product(product_id, session['toko_id'])
    return jsonify(result)


@dashboard_bp.route('/subscription-inactive')
def subscription_inactive():
    """Page shown to merchants with inactive (CANCELLED/EXPIRED) subscriptions"""
    toko_id = session.get('toko_id')
    if not toko_id:
        return redirect(url_for('dashboard.login'))
    
    from app.models import Subscription, Toko
    sub = Subscription.query.filter_by(phone_number=toko_id).first()
    toko = Toko.query.get(toko_id)
    
    return render_template('dashboard/subscription_inactive.html', 
                          subscription=sub, 
                          toko=toko)

@dashboard_bp.route('/')
@login_required
def index():
    toko = Toko.query.get(session['toko_id'])
    
    # Basic Stats
    total_customers = Customer.query.filter_by(toko_id=toko.id).count()
    total_chats = ChatLog.query.filter_by(toko_id=toko.id).count()
    
    # Recent Customers
    recent_customers = Customer.query.filter_by(toko_id=toko.id)\
        .order_by(Customer.last_interaction.desc()).limit(10).all()
        
    # API Settings for this store (stored as prefix_key or global for simple setup)
    # Here we use SystemConfig to store per-store/global depending on architecture
    # For now, let's fetch based on the store phone number if possible
    # Get system config for the template
    from app.models import Subscription
    subscription = Subscription.query.filter_by(phone_number=toko.id).first()
    
    # Get system config (instructions, model)
    instructions_cfg = SystemConfig.query.get(f"system_instructions_{toko.id}")
    system_config = {
        'system_instructions': instructions_cfg.value if instructions_cfg else ''
    }
    
    # Placeholder chart data
    chart_data = [0, 0, 0, 0, 0, 0, 0]  # Last 7 days
    
    # Trial onboarding banner
    show_trial_banner = False
    trial_days_remaining = 0
    trial_hours_remaining = 0
    if subscription and subscription.tier == 'TRIAL' and subscription.status == 'ACTIVE':
        if subscription.expired_at:
            time_remaining = subscription.expired_at - datetime.now()
            trial_days_remaining = max(0, time_remaining.days)
            trial_hours_remaining = max(0, (time_remaining.seconds // 3600) if time_remaining.days == 0 else 0)
            show_trial_banner = True

    return render_template('dashboard/index.html', 
                           toko=toko, 
                           total_customers=total_customers,
                           total_chats=total_chats,
                           recent_customers=recent_customers,
                           subscription=subscription,
                           system_config=system_config,
                           chart_data=chart_data,
                           show_trial_banner=show_trial_banner,
                           trial_days_remaining=trial_days_remaining,
                           trial_hours_remaining=trial_hours_remaining)

@dashboard_bp.route('/api/stats')
@login_required
def api_stats():
    toko_id = session['toko_id']
    # Example: Chat volume last 7 days
    dates = []
    counts = []
    now = datetime.now()
    for i in range(6, -1, -1):
        d = now - timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        c = ChatLog.query.filter(
            ChatLog.toko_id == toko_id, 
            db.func.date(ChatLog.created_at) == d.date()
        ).count()
        dates.append(d_str)
        counts.append(c)
        
    return jsonify({"labels": dates, "data": counts})

@dashboard_bp.route('/test_api', methods=['POST'])
@login_required
def test_api():
    data = request.json
    api_key = data.get('apiKey')
    if not api_key:
        return jsonify({"status": "error", "error": "API Key kosong"}), 400
        
    try:
        from google import genai
        test_client = genai.Client(api_key=api_key)
        # Simple test call
        res = test_client.models.generate_content(
            model='gemini-2.0-flash', # Default System Model
            contents="Say 'OK' if you see this."
        )
        if res and res.text:
            return jsonify({"status": "success"})
        return jsonify({"status": "error", "error": "No response from AI"}), 500
    except Exception as e:
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg:
            error_msg = "API Key tidak valid (Check di AI Studio)"
        return jsonify({"status": "error", "error": error_msg}), 400

@dashboard_bp.route('/save_settings', methods=['POST'])
@login_required
def save_settings():
    toko_id = session['toko_id']
    data = request.json
    api_key = data.get('apiKey')
    try:
        # Save API Key
        cfg_key = SystemConfig.query.get(f"gemini_api_key_{toko_id}")
        if not cfg_key: cfg_key = SystemConfig(key=f"gemini_api_key_{toko_id}")
        cfg_key.value = api_key
        db.session.add(cfg_key)
        
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "error": str(e)}), 500

@dashboard_bp.route('/delete_data', methods=['POST'])
@login_required
def delete_data():
    toko_id = session['toko_id']
    try:
        # Delete Chat Logs
        ChatLog.query.filter_by(toko_id=toko_id).delete()
        
        # Reset Customer statuses but keep the customers
        customers = Customer.query.filter_by(toko_id=toko_id).all()
        for c in customers:
            c.order_status = 'NONE'
            c.current_bill = 0
            c.followup_status = 'NONE'
            c.last_context = ""
            
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "error": str(e)}), 500

# --- Order Management Routes (NEW) ---

@dashboard_bp.route('/orders')
@login_required
def orders():
    toko_id = session['toko_id']
    toko = Toko.query.get(toko_id)
    
    # Get status filter
    status_filter = request.args.get('status', 'ALL')
    
    query = Transaction.query.filter_by(toko_id=toko_id)
    
    if status_filter == 'PENDING':
        query = query.filter(Transaction.status == 'PENDING')
    elif status_filter == 'MANUAL_REVIEW':
        query = query.filter(Transaction.verification_status == 'MANUAL_REVIEW')
    elif status_filter == 'PAID':
        query = query.filter(Transaction.status == 'PAID')
    elif status_filter == 'CANCELLED':
        query = query.filter(Transaction.status == 'CANCELLED')
    
    # Sort by newest
    orders = query.order_by(Transaction.created_at.desc()).limit(100).all()
    
    return render_template('dashboard/orders.html', toko=toko, orders=orders, filter=status_filter)

@dashboard_bp.route('/orders/<order_id>/verify', methods=['POST'])
@login_required
def verify_order_manual(order_id):
    toko_id = session['toko_id']
    data = request.json
    action = data.get('action') # APPROVE or REJECT
    notes = data.get('notes', '')
    
    # Security: Ensure order belongs to this store
    order = Transaction.query.filter_by(order_id=order_id, toko_id=toko_id).first()
    if not order:
        return jsonify({"status": "error", "message": "Order not found"}), 404
        
    try:
        from app.services.order_service import verify_order
        
        if action == 'APPROVE':
            verify_order(
                order_id=order_id,
                verification_status='VERIFIED',
                verified_by=f"MANUAL:{toko_id}",
                notes=notes
            )
            
            # Send notification to customer
            from app.services.waha import kirim_waha
            toko = Toko.query.get(toko_id)
            if toko.session_name:
                msg = (
                    f"✅ *Pembayaran Diterima!*\n\n"
                    f"Order #{order_id} telah dikonfirmasi oleh admin.\n"
                    f"Terima kasih sudah berbelanja! 🙏"
                )
                kirim_waha(order.customer_hp, msg, toko.session_name)
                
        elif action == 'REJECT':
            verify_order(
                order_id=order_id,
                verification_status='REJECTED',
                verified_by=f"MANUAL:{toko_id}",
                notes=notes
            )
            
            toko = Toko.query.get(toko_id)
            if toko.session_name:
                msg = (
                    f"❌ *Pembayaran Ditolak*\n\n"
                    f"Order #{order_id} belum dapat diverifikasi.\n"
                    f"Alasan: {notes}\n"
                    f"Silakan hubungi admin untuk info lebih lanjut."
                )
                kirim_waha(order.customer_hp, msg, toko.session_name)
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- Analytics Routes (NEW) ---

@dashboard_bp.route('/analytics')
@login_required
def analytics():
    toko_id = session['toko_id']
    toko = Toko.query.get(toko_id)
    
    # Get basic metrics for initial load
    from app.services.analytics_service import get_key_metrics, get_top_products
    metrics = get_key_metrics(toko_id)
    top_products = get_top_products(toko_id)
    
    return render_template('dashboard/analytics.html', toko=toko, metrics=metrics, top_products=top_products)

@dashboard_bp.route('/api/analytics/sales')
@login_required
def api_sales_analytics():
    toko_id = session['toko_id']
    days = int(request.args.get('days', 30))
    
    from app.services.analytics_service import get_sales_chart_data
    data = get_sales_chart_data(toko_id, days)
    
    return jsonify(data)

@dashboard_bp.route('/api/analytics/export/transactions')
@login_required
def export_transactions():
    toko_id = session['toko_id']
    import csv
    import io
    from flask import Response
    
    # Fetch all PAID transactions
    transactions = Transaction.query.filter_by(
        toko_id=toko_id,
        status='PAID'
    ).order_by(Transaction.created_at.desc()).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Order ID', 'Date', 'Customer Phone', 'Amount', 'Detected Bank', 'Confidence', 'Items'])
    
    # Rows
    for t in transactions:
        writer.writerow([
            t.order_id,
            t.verified_at.strftime("%Y-%m-%d %H:%M") if t.verified_at else t.created_at.strftime("%Y-%m-%d %H:%M"),
            t.customer_hp,
            t.nominal,
            t.detected_bank or '-',
            f"{t.confidence_score}%" if t.confidence_score else '-',
            t.items_json or '-'
        ])
        
    output.seek(0)
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=transactions_{toko_id}.csv"}
    )

@dashboard_bp.route('/api/analytics/export/customers')
@login_required
def export_customers():
    toko_id = session['toko_id']
    import csv
    import io
    from flask import Response
    
    customers = Customer.query.filter_by(toko_id=toko_id).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Phone Number', 'Last Interaction', 'Total Bill', 'Status'])
    
    for c in customers:
        writer.writerow([
            c.nomor_hp,
            c.last_interaction.strftime("%Y-%m-%d %H:%M"),
            c.current_bill,
            c.order_status
        ])
        
    output.seek(0)
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=customers_{toko_id}.csv"}
    )
