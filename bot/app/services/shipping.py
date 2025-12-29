import requests
import logging
from app.config import Config

API_KEY = Config.RAJAONGKIR_API_KEY
BASE_URL = Config.RAJAONGKIR_BASE_URL

# Caching simple (in-memory) to avoid repeated city searches
CITY_CACHE = []

def get_headers():
    return {'key': API_KEY}

def search_city(query):
    """
    Search city by name. Returns list of matches.
    """
    global CITY_CACHE
    try:
        # Load cache if empty
        if not CITY_CACHE:
            logging.info("Loading RajaOngkir cities...")
            res = requests.get(f"{BASE_URL}/city", headers=get_headers(), timeout=10)
            if res.status_code == 200:
                results = res.json()['rajaongkir']['results']
                CITY_CACHE = results
            else:
                logging.error(f"RajaOngkir Error: {res.text}")
                return []
        
        # Filter
        query = query.lower()
        matches = []
        for c in CITY_CACHE:
            full_name = f"{c['type']} {c['city_name']}"
            if query in full_name.lower():
                matches.append({
                    'id': c['city_id'],
                    'name': full_name,
                    'province': c['province']
                })
        return matches[:10] # Limit suggestions
        
    except Exception as e:
        logging.error(f"Search City Error: {e}")
        return []

def get_shipping_cost(origin_id, destination_id, weight=1000, courier="jne"):
    """
    Check shipping cost.
    """
    try:
        url = f"{BASE_URL}/cost"
        payload = {
            "origin": origin_id,
            "destination": destination_id,
            "weight": weight,
            "courier": courier
        }
        res = requests.post(url, data=payload, headers=get_headers(), timeout=10)
        data = res.json()
        
        if data['rajaongkir']['status']['code'] == 200:
            costs = data['rajaongkir']['results'][0]['costs']
            result_text = []
            for c in costs:
                service = c['service']
                cost = c['cost'][0]['value']
                etd = c['cost'][0]['etd']
                result_text.append(f"{courier.upper()} {service}: Rp {cost:,} ({etd} hari)")
            return "\n".join(result_text)
        else:
            return "Gagal memuat ongkir."
            
    except Exception as e:
        logging.error(f"Get Cost Error: {e}")
        return "Gagal koneksi kurir."

def get_city_name(city_id):
    global CITY_CACHE
    # Ensure cache loaded (simplified logic, ideally shared)
    if not CITY_CACHE: search_city("jakarta") 
    
    for c in CITY_CACHE:
        if str(c['city_id']) == str(city_id):
            return f"{c['type']} {c['city_name']}"
    return "Unknown City"
