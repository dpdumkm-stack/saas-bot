
import sys
import os

# Add bot directory to path
sys.path.append(os.path.join(os.getcwd(), 'bot'))

from app.utils import should_ignore_message

def test_should_ignore():
    # TestCase 1: Normal user chat (Should Pass)
    payload_normal = {
        'payload': {
            'from': '628123456789@c.us',
            'fromMe': False,
            'body': 'Halo bot'
        }
    }
    ignore, reason = should_ignore_message(payload_normal)
    print(f"Test 1 (Normal): Ignore={ignore} (Expected False)")
    assert ignore == False

    # TestCase 2: Self-Chat with text (Should Ignore)
    payload_self_text = {
        'payload': {
            'from': '628123456789@c.us',
            'fromMe': True,
            'body': 'Catatan belanja'
        }
    }
    ignore, reason = should_ignore_message(payload_self_text)
    print(f"Test 2 (Self Text): Ignore={ignore}, Reason={reason} (Expected True, from_me)")
    assert ignore == True

    # TestCase 3: Self-Chat with Command (Should Pass - THE BYPASS)
    payload_self_cmd = {
        'payload': {
            'from': '628123456789@c.us',
            'fromMe': True,
            'body': '/unreg'
        }
    }
    ignore, reason = should_ignore_message(payload_self_cmd)
    print(f"Test 3 (Self Cmd): Ignore={ignore} (Expected False)")
    assert ignore == False

    print("✅ All Tests Passed!")

if __name__ == "__main__":
    test_should_ignore()
