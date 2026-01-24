import random
import time
from datetime import datetime
import logging

class Humanizer:
    # 1. Bank Karakter Tak Kasat Mata (DNA Unik)
    # Zero Width Space (U+200B) & Zero Width Non-Joiner (U+200C)
    INVISIBLE_CHARS = ['\u200b', '\u200c']
    
    # 2. Bank Sapaan Dinamis (Greeting Drift)
    GREETINGS = {
        'morning': ['Selamat pagi', 'Pagi', 'Met pagi', 'Pagi Kak', 'Halo, selamat pagi'],
        'afternoon': ['Selamat siang', 'Siang Kak', 'Met siang', 'Halo Kak', 'Siang'],
        'evening': ['Selamat sore', 'Sore Kak', 'Met sore', 'Halo', 'Sore'],
        'night': ['Selamat malam', 'Malam Kak', 'Met malam', 'Halo Kak', 'Malam']
    }
    
    # 3. Bank Slang (Human Singkatan)
    SLANG_MAP = {
        'sudah': ['sdh', 'udah', 'udh'],
        'belum': ['blm', 'belom'],
        'saya': ['sy', 'aku'],
        'kamu': ['km', 'kakak', 'kak'],
        'terima kasih': ['tks', 'makasih', 'mksih'],
        'siap': ['siap', 'ok', 'oke'],
        'dengan': ['dg', 'dgn'],
        'ada': ['ada', 'ad'],
        'tidak': ['gk', 'gak', 'tdk']
    }

    # 4. Bank Emoji Natural
    EMOJI_BANK = ['😊', '🙏', '👍', '👌', '✨', '👋', '🔥']

    @staticmethod
    def get_invisible_fingerprint(length=3):
        """Menghasilkan 'sidik jari' tak kasat mata."""
        return "".join(random.choice(Humanizer.INVISIBLE_CHARS) for _ in range(length))

    @staticmethod
    def get_dynamic_greeting():
        """Memberikan sapaan berdasarkan waktu lokal."""
        hour = datetime.now().hour
        if 5 <= hour < 11:
            key = 'morning'
        elif 11 <= hour < 15:
            key = 'afternoon'
        elif 15 <= hour < 19:
            key = 'evening'
        else:
            key = 'night'
        
        return random.choice(Humanizer.GREETINGS[key])

    @staticmethod
    def apply_slang_variation(text):
        """Mengganti beberapa kata baku menjadi slang/singkatan (probabilitas 30%)."""
        if not text: return text
        
        # Split by lines explicitly to preserve paragraphs
        lines = text.split('\n')
        processed_lines = []
        
        for line in lines:
            # Skip empty lines, just append them back
            if not line.strip():
                processed_lines.append(line)
                continue
                
            words = line.split()
            new_words = []
            for word in words:
                clean_word = word.lower().strip(",.!?")
                if clean_word in Humanizer.SLANG_MAP and random.random() < 0.3:
                    variation = random.choice(Humanizer.SLANG_MAP[clean_word])
                    # Jaga tanda baca asli
                    new_words.append(word.lower().replace(clean_word, variation))
                else:
                    new_words.append(word)
            processed_lines.append(" ".join(new_words))
            
        return "\n".join(processed_lines)

    @staticmethod
    def apply_punctuation_drift(text):
        """Memberikan variasi tanda baca di akhir kalimat."""
        if text.endswith('.'):
            rand = random.random()
            if rand < 0.3: return text[:-1] # Hapus titik
            if rand < 0.5: return text + ".." # Double titik
            if rand < 0.6: return text + "..." # Triple titik
        return text

    @staticmethod
    def apply_mid_word_fingerprint(text):
        """
        Menyisipkan karakter invisible di sela-sela kata (SANGAT RAHASIA).
        Skips emoji and special characters to avoid corruption.
        """
        if len(text) < 10:
            return text
        
        # Split by spaces to get words
        words = text.split()
        if not words:
            return text
        
        # Only target simple ASCII words (skip emoji and special chars)
        safe_words = []
        for idx, word in enumerate(words):
            # Check if word is safe (contains only ASCII letters)
            if word and len(word) > 3 and word.isascii() and not any(c in word for c in '🏓😊🙏👍👌✨👋🔥'):
                safe_words.append((idx, word))
        
        if not safe_words:
            return text  # No safe words to fingerprint
        
        # Pick one safe word randomly
        idx, target_word = random.choice(safe_words)
        mid = len(target_word) // 2
        words[idx] = target_word[:mid] + random.choice(Humanizer.INVISIBLE_CHARS) + target_word[mid:]
        
        return " ".join(words)

    @staticmethod
    def humanize_text(text, add_greeting=False):
        """
        Wrapper utama untuk memanusiakan pesan (VOID LEVEL).
        Fixed to avoid emoji corruption.
        """
        if not text:
            return text
        
        processed = text
        
        # 1. Apply Slang (safe, doesn't touch emoji)
        processed = Humanizer.apply_slang_variation(processed)
        
        # 2. Apply Punctuation Drift (safe, only affects end punctuation)
        processed = Humanizer.apply_punctuation_drift(processed)
        
        # 3. Add Greeting (Optional)
        if add_greeting:
            processed = f"{Humanizer.get_dynamic_greeting()}! {processed}"
            
        # 4. Add Random Emoji (20% chance) - placed at end to avoid corruption
        if random.random() < 0.2:
            processed += " " + random.choice(Humanizer.EMOJI_BANK)
            
        # 5. Mid-word fingerprint (DISABLED FOR RELIABILITY)
        # processed = Humanizer.apply_mid_word_fingerprint(processed)
        
        # 6. Add invisible fingerprint (DISABLED FOR RELIABILITY)
        # if not any(emoji in processed[-5:] if len(processed) >= 5 else processed for emoji in Humanizer.EMOJI_BANK):
        #    processed += Humanizer.get_invisible_fingerprint(random.randint(1, 2))
        
        return processed

    @staticmethod
    def get_adaptive_delay(text):
        """Menghitung delay 'Mikir' dan ngetik (NUKLIR LEVEL)."""
        # Kecepatan ngetik: ~0.05s per char (admin cepat)
        base_typing_sec = len(text) * 0.05
        
        # Jeda Mikir (Latency)
        # Jika teks panjang/ada tanda tanya, admin mikir lebih lama
        latency = random.uniform(1.0, 3.0)
        if len(text) > 100 or '?' in text:
            latency += random.uniform(1.0, 2.0)
            
        # Noise ±15%
        noise = random.uniform(0.85, 1.15)
        
        return {
            'latency': latency,
            'typing': base_typing_sec * noise
        }
