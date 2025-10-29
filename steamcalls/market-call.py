import json
import os
import time
from dotenv import load_dotenv
from urllib.request import urlopen
import urllib.parse
import webbrowser
import threading
import datetime
import sys

load_dotenv(override=True)

MARKET_LINK=os.getenv("MARKET_ASC_UNUSUAL_LINK")
MAX_PRICE=os.getenv("MAX_PRICE")
MAX_PRICE=int(MAX_PRICE) 

# Caches so we don't repeat spam output
last_item_name = None
last_item_price = None

paused = False
running = True

def FetchMarket():
    try:
        with urlopen(MARKET_LINK) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("⚠️ Too many requests: waiting 60 seconds...")
            time.sleep(60)
            return None
        else:
            print(f"HTTP Error {e.code}: {e.reason}")
            return None
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

    
def ParseData(raw_json):
    global last_item_name, last_item_price
    
    try:
        data=json.loads(raw_json)
        if not data.get('success'):
            print("⚠️ Unsuccessful response from Steam API.")
            return
        
        result = data.get("results", [{}])[0]
        name = result.get("name")
        sell_int = result.get("sell_price")
        sell_text = result.get("sell_price_text")
        possible_sell_price=(sell_int - 960) / 100 if sell_int is not None else None
        
        if name is None or sell_int is None:
            print("⚠️ Incomplete data received.")
            return
        
        if last_item_name != name or last_item_price != sell_int:
            print(f"Item Name: {name}")
            print(f"Item sell price: {sell_text}")
            print(f"Possible sell price: ${possible_sell_price:.2f}")
            last_item_name = name
            last_item_price = sell_int
        
        if possible_sell_price < MAX_PRICE:
            makeOpenUrl(name)
            
    except Exception as e:
        print(f"Error parsing data: {e}")
        return

def makeOpenUrl(name):
    base_url = "https://steamcommunity.com/market/listings/730/"
    encoded_name = urllib.parse.quote(name)
    
    full_url = base_url + encoded_name
    print(f"➡️ Opened listing for '{name}' in browser.")
    webbrowser.open(full_url)
        
def PriceCheckLoop():
    print("✅ Price monitoring started. Checking every 5 minutes.\n")
    
    while True:
        raw=FetchMarket()
        if raw:
            ParseData(raw)
        time.sleep(5*60)  # Check every 5 minutes
        
def keyboard_listener():
    """Listens for keyboard input."""
    global paused, running

    while running:
        key = sys.stdin.readline().strip().lower()

        if key == "p":
            paused = not paused
            print("▶️ Resumed" if not paused else "⏸ Paused")

        elif key == "s":
            print("🛑 Stopping application...")
            running = False
            break
            
def start():
    # Thread: price checking
    t1 = threading.Thread(target=PriceCheckLoop, daemon=True)
    t1.start()

    # Thread: keyboard input
    t2 = threading.Thread(target=keyboard_listener, daemon=True)
    t2.start()

    # Keep main alive until stop is requested
    while running:
        time.sleep(0.5)

    print("✅ Application closed.")
    

if __name__ == "__main__":
    start()