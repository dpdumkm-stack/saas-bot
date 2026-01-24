from app import create_app
from app.models import Subscription, Toko
from app.extensions import db
from datetime import datetime, timedelta
import uuid

app = create_app()

def create_dummy():
    with app.app_context():
        # 1. Check if dummy already exists
        order_id = "DUMMY-QR-TEST"
        phone = "1234567890"
        
        sub = Subscription.query.filter_by(order_id=order_id).first()
        if sub:
            print(f"Dummy {order_id} already exists. Updating...")
        else:
            print(f"Creating new dummy subscription {order_id}...")
            sub = Subscription(order_id=order_id, phone_number=phone)
            db.session.add(sub)
        
        sub.name = "Test User"
        sub.category = "F&B"
        sub.status = "ACTIVE"
        sub.payment_status = "paid"
        sub.tier = "TRIAL"
        sub.expired_at = datetime.now() + timedelta(days=7)
        
        # 2. Ensure Toko exists
        toko = Toko.query.get(phone)
        if not toko:
            print(f"Creating associated Toko record for {phone}...")
            toko = Toko(
                id=phone,
                nama="Toko Test QR",
                kategori="F&B",
                session_name=f"session_{phone}",
                remote_token=str(uuid.uuid4())[:8]
            )
            db.session.add(toko)
        
        db.session.commit()
        print(f"✅ Success! Dummy created.")
        print(f"🔗 URL: https://saas-bot-643221888510.asia-southeast2.run.app/success?order_id={order_id}")

if __name__ == "__main__":
    create_dummy()
