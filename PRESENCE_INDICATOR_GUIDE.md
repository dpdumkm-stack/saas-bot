# Presence Indicator Testing & Configuration Guide

## 📋 Step-by-Step Instructions

### **STEP 1: Test WAHA Presence Support**

**Run test script:**
```powershell
python test_presence_indicator.py
```

**What it does:**
1. Asks for your WhatsApp number
2. Sends "composing" presence to WAHA
3. Waits 10 seconds (you check WhatsApp)
4. Stops "composing" presence
5. Asks if you saw "sedang mengetik..."

**Expected interaction:**
```
Masukkan nomor WhatsApp Anda untuk test (628xxx): 6285178272760

STEP 1: Activating 'typing...' indicator
Response: HTTP 200

STEP 2: Waiting 10 seconds...
🔍 CHECK YOUR WHATSAPP NOW!
   Apakah Anda melihat 'sedang mengetik...'?

STEP 3: Stopping 'typing...' indicator
Response: HTTP 200

Apakah Anda melihat 'sedang mengetik...' di WhatsApp? (y/n):
```

---

### **STEP 2A: If Presence WORKING (y)**

✅ **Good news!** WAHA supports presence indicator.

**Enable adaptive delay for better visibility:**

**File:** `bot/app/routes/webhook.py`

**Find line** (~316):
```python
kirim_waha(chat_id, ai_response, session_id)
```

**Replace with:**
```python
kirim_waha(chat_id, ai_response, session_id, use_adaptive_delay=True)
```

**What this does:**
- Short messages (< 20 chars): 2-3s delay
- Medium messages (20-100 chars): 3-6s delay
- Long messages (> 100 chars): 5-8s delay
- Messages with "?": +1-2s thinking time

**Result:** "Sedang mengetik..." akan visible lebih lama & natural!

**Deploy:**
```powershell
.\safe_deploy.ps1
```

---

### **STEP 2B: If Presence NOT WORKING (n)**

⚠️ **WAHA doesn't support presence or not visible**

**Option 1: Keep Current (Recommended)**
- Current delays still work (1.5-3s)
- Anti-spam masih efektif
- No changes needed
- **Just deploy as-is**

**Option 2: Disable Presence Calls (Clean)**
Jika mau disable presence calls untuk avoid timeout errors:

**File:** `bot/app/services/waha.py:92-104`

**Comment out:**
```python
# Show "typing..." indicator
# set_presence(chat_id, "composing", session_name)  # DISABLED

# Typing delay (still active!)
if add_delay:
    delay = random.uniform(1.5, 3.0)
    time.sleep(delay)

# Send
kirim_waha_raw(chat_id, text, session_name)

# Stop typing (disabled)
# set_presence(chat_id, "available", session_name)  # DISABLED
```

**Result:** No presence API calls, delays still work, cleaner logs

---

## 🎯 Current Implementation

### **Features Already Active:**

1. ✅ **Typing Delay**: 1.5-3s random (or adaptive if enabled)
2. ✅ **Presence Calls**: Attempt to show "typing..."
3. ✅ **Fallback**: If presence fails, message still sends
4. ✅ **Error Handling**: Silent failure, doesn't break bot

### **New Feature (Optional):**

- ✅ **Adaptive Delay**: Smart delay based on message length
- ✅ **Parameter**: `use_adaptive_delay=True` (default: False)

**To enable globally**, edit:
```python
# File: waha.py:80
def kirim_waha(..., use_adaptive_delay=False):
# Change to:
def kirim_waha(..., use_adaptive_delay=True):
```

---

## 📊 Delay Comparison

| Message Type | Current (Random) | Adaptive | Visibility |
|--------------|------------------|----------|------------|
| "Ok" (2 chars) | 1.5-3s | 2-3s | Low |
| "Baik Kak..." (20 chars) | 1.5-3s | 3-4s | Medium |
| "Terima kasih..." (100 chars) | 1.5-3s | 5-7s | High |
| Long AI response | 1.5-3s | 7-8s (capped) | Very High |

**Recommendation:** Use adaptive for better UX

---

## ✅ Quick Decision Tree

```
Test presence → Working? 
                ├─ YES → Enable adaptive delay → Deploy
                └─ NO  → Keep current OR disable presence → Deploy
```

---

## 🚀 Next Steps

1. **Run test:** `python test_presence_indicator.py`
2. **Based on result:**
   - Working → Enable adaptive
   - Not working → Keep current
3. **Deploy:** `.\safe_deploy.ps1`

---

**Files Updated:**
- ✅ `test_presence_indicator.py` - Test script
- ✅ `waha.py` - Added adaptive delay support
- ✅ `PRESENCE_INDICATOR_GUIDE.md` - This guide

**Status:** 🟢 Ready for testing & deployment!
