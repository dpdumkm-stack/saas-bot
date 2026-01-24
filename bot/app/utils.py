import logging
from app.config import Config
import re

def should_ignore_message(data):
    """
    Unified filter to ignore unwanted messages (groups, status, etc.)
    """
    msg_obj = data.get('payload', data.get('data', data))
    chat_id = msg_obj.get('from') or msg_obj.get('chatId') or ""
    
    # 1. Identity filters
    if any(x in chat_id for x in ["@g.us", "status@broadcast", "@newsletter"]):
        return True, "non_personal_chat"
        
    # 2. Origin filters
    payload = data.get('payload', {})
    from_me = payload.get('fromMe', False)
    if from_me:
        # ALLOW owner commands (starting with /) to pass through
        body = msg_obj.get('body', '')
        if not (body and body.startswith('/')):
            return True, "from_me"
        
    if not (chat_id or msg_obj.get('body')):
        return True, "empty_payload"
        
    return False, None

def get_parsed_number(data):
    """Extract clean phone number from various payload structures"""
    msg_obj = data.get('payload', data.get('data', data))
    chat_id = msg_obj.get('from') or msg_obj.get('chatId') or ""
    
    nomor_murni = chat_id.split('@')[0] if '@' in chat_id else chat_id
    
    # Handle WAHA LID (Linked Device ID) format
    # When from field is @lid (e.g., 254369639469251@lid), try to get real chat ID from other fields
    if '@lid' in chat_id.lower():
        # Priority 1: Check chatId field (often has the correct @c.us format)
        real_chat_id = msg_obj.get('chatId', '')
        if real_chat_id and '@c.us' in real_chat_id:
            chat_id = real_chat_id
            nomor_murni = chat_id.split('@')[0]
        else:
            # Priority 2: Check _data.key.remoteJid
            remote_jid = msg_obj.get('_data', {}).get('key', {}).get('remoteJid', '')
            if remote_jid and '@c.us' in remote_jid:
                chat_id = remote_jid
                nomor_murni = chat_id.split('@')[0]
    
    # Handle WAHA Alt JID (alternative JID mapping)
    alt_jid = msg_obj.get('_data', {}).get('key', {}).get('remoteJidAlt', '')
    if alt_jid and "@c.us" in alt_jid:
        nomor_murni = alt_jid.split('@')[0]
        chat_id = alt_jid
        
    return nomor_murni, chat_id

def normalize_phone_number(phone: str, validate_indonesia: bool = False) -> str:
    """
    Normalize various phone formats to 628...
    Input:
    - 0812345 (local)
    - 62812345 (international)
    - +62812345 (plus)
    - 081-234 (dash)
    - 62 812 (space)
    
    Output:
    - 62812345 (or None if validate_indonesia=True and format is invalid)
    """
    if not phone:
        return "" if not validate_indonesia else None
        
    # 1. Remove all non-digit characters
    digits = re.sub(r'\D', '', str(phone))
    
    # 2. Handle prefixes
    if digits.startswith('0'):
        # 0812... -> 62812...
        digits = '62' + digits[1:]
    elif digits.startswith('8'):
        # 812... -> 62812...
        digits = '62' + digits
    # If starts with 62, it's already in international format
    
    # 3. Validation (Optional)
    if validate_indonesia:
        # Indonesian numbers are 10-13 digits after 62 (Total 12-15 digits)
        if len(digits) < 11 or len(digits) > 15:
            return None
        
        if not digits.startswith('628'):
            return None
            
    return digits
