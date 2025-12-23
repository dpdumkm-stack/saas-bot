import requests
import re

def download_file(url):
    try:
        res = requests.get(url)
        return res.content, res.headers.get('Content-Type')
    except: return None, None

def extract_number(text):
    try:
        nums = re.findall(r'\d+', text.replace('.', '').replace(',', ''))
        return int(nums[0]) if nums else 0
    except: return 0
