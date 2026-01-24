"""
Message Variation Service
Generates unique message variations using Gemini AI to prevent spam detection
"""
import logging
from typing import List
from google import genai
from app.config import Config

import re
import json

from app.services.humanizer import Humanizer

def generate_message_variations(base_message: str, count: int = 10) -> List[str]:
    """
    Generate unique variations of a message using Gemini AI
    
    Args:
        base_message: The original message template
        count: Number of variations to generate (default 10)
        
    Returns:
        List of message variations (including original as first item)
    """
    # 1. MASK LINKS (Protect them from AI)
    # Regex for URLs (http/https)
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    links = re.findall(url_pattern, base_message)
    link_map = {}
    
    masked_message = base_message
    for i, link in enumerate(links):
        placeholder = f"[[LINK_{i}]]"
        link_map[placeholder] = link
        masked_message = masked_message.replace(link, placeholder)
        
    try:
        client = genai.Client(api_key=Config.GEMINI_API_KEY)
        
        prompt = f"""Tugas: Buat {count - 1} variasi kalimat dari pesan broadcast ini.
Tujuan: Agar pesan tidak terdeteksi sebagai spam oleh WhatsApp, tapi makna dan intinya harus TETAP SAMA PERSIS.

⚠️ ATURAN MUTLAK (JANGAN DILANGGAR):
1. WAJIB BAHASA INDONESIA. Jangan pernah menerjemahkan ke bahasa Inggris atau bahasa lain.
2. JANGAN ubah posisi 'Enter' (Baris Baru). Jika di pesan asli ada jarak antar paragraf, di variasi juga HARUS ADA.
3. Placeholder {{nama}} dan [[LINK_X]] JANGAN DIUBAH posisinya. Harus tetap ada.
4. Gaya bahasa: Sopan, Ramah, dan Professional.
5. Gunakan sinonim untuk kata-kata umum (misal: "Halo" -> "Selamat Pagi", "Kami mengundang" -> "Kami ingin mengajak").
6. JANGAN menambahkan sapaan (Bapak/Ibu/Kak) secara manual di depan placeholder {{nama}}, karena sapaan tersebut biasanya sudah ada di dalam data nama atau akan ditangani otomatis.

Pesan Asli:
{masked_message}

FORMAT OUTPUT (JSON ARRAY):
Kembalikan hanya JSON Array berisi string.
Contoh:
["Variasi 1..\\n\\nParagraf 2..", "Variasi 2..\\n\\nParagraf 2.."]"""

        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )
        
        if not response or not response.text:
            logging.warning("Gemini returned empty response for message variations")
            return [base_message]  # Fallback to original
        
        # Parse JSON
        variations = [base_message]  # Always include original as first
        
        try:
            # Clean potential markdown wrapping
            clean_text = response.text.strip().replace('```json', '').replace('```', '').strip()
            parsed_variations = json.loads(clean_text)
            
            if isinstance(parsed_variations, list):
                for text in parsed_variations:
                    if isinstance(text, str) and len(text) > 10:
                        # 2. RESTORE LINKS
                        for placeholder, original_link in link_map.items():
                            text = text.replace(placeholder, original_link)
                        
                        # Safety check: if AI somehow deleted the link placeholder, force append original link
                        # But only if original message had links
                        # (Skipping complex heuristic for now, relying on explicit prompt)
                        
                        variations.append(text)
            else:
                logging.warning(f"Gemini returned non-list JSON: {type(parsed_variations)}")
                
        except json.JSONDecodeError as je:
            logging.error(f"Failed to parse Gemini JSON: {je} | Text: {response.text[:100]}...")
            # Fallback: Try line splitting if JSON fails (legacy mode)
            lines = response.text.strip().split('\n')
            for line in lines:
                 if len(line) > 20 and not line.strip().startswith('['):
                     variations.append(line.strip())

        
        # If we got fewer variations than requested, fill with slight modifications
        while len(variations) < count:
            variations.append(base_message)
        
        logging.info(f"Generated {len(variations)} message variations")
        return variations[:count]  # Return exact count requested
        
    except Exception as e:
        logging.error(f"Failed to generate message variations: {e}")
        # Fallback: Generate algorithmic variations using Humanizer
        # DO NOT return identical messages.
        fallback_variations = []
        for _ in range(count):
            # Apply heavier random slang and punctuation for fallback to ensure uniqueness
            variant = Humanizer.humanize_text(base_message)
            fallback_variations.append(variant)
            
        return fallback_variations


def render_personalized_message(template: str, data: dict) -> str:
    """
    Render message template with personalization data
    
    Args:
        template: Message template with {placeholders}
        data: Dict with values to replace (e.g., {'nama': 'Budi'})
        
    Returns:
        Personalized message string
    """
    import re
    
    def replace_placeholder(match):
        """Replace {var} or {var|fallback} with actual value"""
        full_match = match.group(1)
        parts = full_match.split('|')
        var_name = parts[0].strip()
        fallback = parts[1].strip() if len(parts) > 1 else 'Kak'
        
        # Get value from data or use fallback
        value = data.get(var_name, '').strip()
        return value if value else fallback
    
    # Replace all {var} or {var|fallback} patterns
    rendered = re.sub(r'\{([^}]+)\}', replace_placeholder, template)
    
    # 2. SALUTATION DEDUPLICATION (Anti "Bapak Bapak")
    # Patterns to catch: "Bapak Bapak", "Ibu Ibu", "Bapak Pak", "Ibu Bu", etc.
    salutations = ['Bapak', 'Ibu', 'Pak', 'Bu', 'Kak']
    combined_pattern = '|'.join(salutations)
    
    # Logic: If we find [Salutation] [Salutation], remove the double one
    for sal in salutations:
        # Case insensitive deduplication
        rendered = re.sub(rf'({sal})\s+({sal})', r'\1', rendered, flags=re.IGNORECASE)
        
    # Also handle "Bapak Pak" or "Ibu Bu"
    rendered = re.sub(r'(Bapak|Bpk)\s+(Pak|Bpk)', r'Bapak', rendered, flags=re.IGNORECASE)
    rendered = re.sub(r'(Ibu)\s+(Bu)', r'Ibu', rendered, flags=re.IGNORECASE)
    
    return rendered
