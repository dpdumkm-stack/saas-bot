import sys
import logging
import os

# Ensure we can import from the 'bot' directory
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

from app import create_app
from app.services.subscription_manager import expire_subscription, permanently_delete_subscription

# Setup simple logging to stdout
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    if len(sys.argv) < 2:
        print("Usage: python manage_subscription.py <phone_number> [mode]")
        print("Modes:")
        print("  (default)  : Soft Freeze (Stop Session, Keep Data)")
        print("  --hard     : Hard Stop (Delete Session, Keep Data)")
        print("  --nuclear  : FULL WIPE (Delete Session AND DATA)")
        return

    phone_number = sys.argv[1]
    mode = "soft"
    
    if len(sys.argv) > 2:
        if sys.argv[2] == "--hard": mode = "hard"
        if sys.argv[2] == "--nuclear": mode = "nuclear"

    app = create_app()
    
    with app.app_context():
        if mode == "nuclear":
            print(f"☢️  WARNING: NUCLEAR MODE SELECTED for {phone_number}")
            print("   This will PERMANENTLY DELETE all data. 5 Seconds to cancel...")
            import time
            time.sleep(5)
            success = permanently_delete_subscription(phone_number)
            if success:
                print(f"\n✅ NUCLEAR WIPE SUCCESSFUL for {phone_number}.")
        else:
            hard_session = (mode == "hard")
            print(f"❄️  Attempting to freeze subscription for: {phone_number} (Session Hard Delete: {hard_session})")
            success = expire_subscription(phone_number, hard_delete_session=hard_session)
            
            if success:
                print(f"\n✅ SUCCESS: Subscription for {phone_number} is frozen.")

if __name__ == "__main__":
    main()
