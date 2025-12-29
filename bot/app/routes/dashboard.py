from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from app.models import Toko, ChatLog, Customer, Transaction
from app.extensions import db
from datetime import datetime, timedelta
import functools

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'toko_id' not in session:
            return redirect(url_for('dashboard.login'))
        return f(*args, **kwargs)
    return decorated_function

@dashboard_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
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
        
    return render_template('dashboard/index.html', 
                           toko=toko, 
                           total_customers=total_customers,
                           total_chats=total_chats,
                           recent_customers=recent_customers)

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
