from datetime import datetime, timedelta
from sqlalchemy import func
from app.extensions import db
from app.models import Transaction, Customer, Menu

def get_sales_chart_data(toko_id: str, days: int = 30):
    """
    Get sales revenue and order count for the last N days.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Query Revenue per day
    revenue_data = db.session.query(
        func.date(Transaction.verified_at).label('date'),
        func.sum(Transaction.nominal).label('revenue'),
        func.count(Transaction.id).label('orders')
    ).filter(
        Transaction.toko_id == toko_id,
        Transaction.status == 'PAID',
        Transaction.verified_at >= start_date
    ).group_by(func.date(Transaction.verified_at)).all()
    
    # Fill missing dates
    dates = []
    revenues = []
    orders = []
    
    revenue_map = {str(r.date): (r.revenue, r.orders) for r in revenue_data}
    
    for i in range(days - 1, -1, -1):
        d = start_date + timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        
        rev, ord_count = revenue_map.get(d_str, (0, 0))
        dates.append(d.strftime("%d %b"))
        revenues.append(int(rev or 0))
        orders.append(ord_count)
        
    return {
        "labels": dates,
        "revenue": revenues,
        "orders": orders
    }

def get_top_products(toko_id: str, limit: int = 5):
    """
    Get top selling products based on transaction history.
    Note: Requires parsing JSON items from transactions.
    For MVP, we might need a simpler approach or dedicated OrderItem table.
    Since we store items as JSON, aggregation is hard in SQL.
    We will pull recent 100 paid orders and aggregate in Python for now.
    """
    import json
    from collections import Counter
    
    cutoff = datetime.now() - timedelta(days=30)
    orders = Transaction.query.filter(
        Transaction.toko_id == toko_id,
        Transaction.status == 'PAID',
        Transaction.verified_at >= cutoff
    ).limit(200).all()
    
    item_counts = Counter()
    item_revenue = Counter()
    
    for o in orders:
        if o.items_json:
            try:
                items = json.loads(o.items_json)
                for i in items:
                    name = i.get('name', 'Unknown')
                    qty = int(i.get('qty', 1))
                    price = int(i.get('price', 0))
                    item_counts[name] += qty
                    item_revenue[name] += (qty * price)
            except:
                continue
                
    # Sort by quantity
    top_items = item_counts.most_common(limit)
    
    result = []
    for name, count in top_items:
        result.append({
            "name": name,
            "count": count,
            "revenue": item_revenue[name]
        })
        
    return result

def get_key_metrics(toko_id: str):
    """
    Get overall key metrics: Total Revenue, Total Orders, Total Customers
    """
    total_revenue = db.session.query(func.sum(Transaction.nominal)).filter(
        Transaction.toko_id == toko_id,
        Transaction.status == 'PAID'
    ).scalar() or 0
    
    total_orders = Transaction.query.filter_by(
        toko_id=toko_id, 
        status='PAID'
    ).count()
    
    total_customers = Customer.query.filter_by(toko_id=toko_id).count()
    
    # Calculate Avg Order Value
    aov = total_revenue / total_orders if total_orders > 0 else 0
    
    # Repeat Customers (Retention)
    repeat_customers = db.session.query(Transaction.customer_hp).filter_by(
        toko_id=toko_id, status='PAID'
    ).group_by(Transaction.customer_hp).having(func.count(Transaction.id) > 1).count()
    
    paid_customers = db.session.query(Transaction.customer_hp).filter_by(
        toko_id=toko_id, status='PAID'
    ).distinct().count()
    
    retention_rate = (repeat_customers / paid_customers * 100) if paid_customers > 0 else 0
    
    return {
        "total_revenue": int(total_revenue),
        "total_orders": total_orders,
        "total_customers": total_customers,
        "aov": int(aov),
        "retention_rate": round(retention_rate, 1),
        "repeat_customers": repeat_customers
    }
