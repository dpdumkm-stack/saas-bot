import sys
import os

# Ensure we can import from the 'bot' directory
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

from app import create_app
from app.models import Toko, Subscription

def list_stores():
    app = create_app()
    with app.app_context():
        print("\n=== DAFTAR TOKO TERDAFTAR ===")
        tokos = Toko.query.all()
        subs = Subscription.query.all()
        
        if not tokos and not subs:
            print("Belum ada toko yang terdaftar.")
            return

        print(f"\nTotal Toko (Tabel Toko): {len(tokos)}")
        print("-" * 60)
        print(f"{'No':<4} {'Phone':<15} {'Nama':<20} {'Session':<20} {'Status Activ':<10}")
        print("-" * 60)
        for i, t in enumerate(tokos, 1):
            print(f"{i:<4} {t.id:<15} {t.nama:<20} {t.session_name:<20} {str(t.status_active):<10}")

        print(f"\nTotal Subscription (Tabel Subscription): {len(subs)}")
        print("-" * 60)
        print(f"{'No':<4} {'Phone':<15} {'Nama':<20} {'Status':<15} {'Tier':<10}")
        print("-" * 60)
        for i, s in enumerate(subs, 1):
            print(f"{i:<4} {s.phone_number:<15} {s.name:<20} {s.status:<15} {s.tier:<10}")
        print("=" * 60)

if __name__ == "__main__":
    list_stores()
