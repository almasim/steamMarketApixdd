import json
import os
import time
from dotenv import load_dotenv
from urllib.request import urlopen
import urllib.parse
import webbrowser
import threading
import requests
import datetime
import sys

load_dotenv(override=True)

MARKET_LINK=os.getenv("MARKET_ASC_UNUSUAL_LINK")
MAX_PRICE=os.getenv("MAX_PRICE")
DISCORD_WEBHOOK=os.getenv("DISCORD_WEBHOOK_URL")
TELEGRAM_TOKEN=os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID")
MAX_PRICE=int(MAX_PRICE) 

# Caches so we don't repeat spam output
last_item_name = None
last_item_price = None

no_change_counter = 0

paused = False
running = True

FETCH_INTERVAL = 30  # in seconds (2 minutes)
last_fetch_time = None

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
    global last_item_name, last_item_price, no_change_counter
    try:
        data=json.loads(raw_json)
        if not data.get('success'):
            print("⚠️ Unsuccessful response from Steam API.")
            return
        
        results = data.get("results", [])
        if not results:
            print("⚠️ No results found.")
            return

        keywords = ["karambit", "butterfly", "flip", "doppler", "m9", "bayonet", "fade", "tigertooth", "crimson", "marble", "gamma", "slaughter", "stiletto"]
        for item in results:
            name = item.get("name", "").lower()
            if any(keyword in name for keyword in keywords):
                print(f"🔗 Keyword match found: {item.get('name')}")
                makeOpenUrl(item.get("name"))
        
        result = data.get("results", [{}])[0]
        name = result.get("name")
        sell_int = result.get("sell_price")
        sell_text = result.get("sell_price_text")
        possible_sell_price=(sell_int - 970) / 100 if sell_int is not None else None
        
        if name is None or sell_int is None:
            print("⚠️ Incomplete data received.")
            return
        
        if last_item_name != name or last_item_price != sell_int:
            print(f"Item Name: {name}")
            print(f"Item sell price: {sell_text}")
            print(f"Possible sell price: ${possible_sell_price:.2f}")
            print(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"----------------------------------------------------------------------")
            last_item_name = name
            last_item_price = sell_int
            no_change_counter = 0
        
        if possible_sell_price < MAX_PRICE:
            makeOpenUrl(name,possible_sell_price)
            
        if last_item_name == name and last_item_price == sell_int:
            no_change_counter += 1
            # print(f"\rNo change in item data... ({no_change_counter})", end="", flush=True)
        
    except Exception as e:
        print(f"Error parsing data: {e}")
        return

def makeOpenUrl(name,possible_sell_price):
    print("✅ Item found below max price! Opening in browser...")
    base_url = "https://steamcommunity.com/market/listings/730/"
    encoded_name = urllib.parse.quote(name)
    
    
    full_url = base_url + encoded_name
    sendDiscordNotification(name, possible_sell_price,full_url)
    sendTelegramNotification(name, possible_sell_price,full_url)
    print(f"➡️ Opened listing for '{name}' in browser.")
    webbrowser.open(full_url)
    
def sendTelegramNotification(item_name, item_price, item_url):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    message = (
        f"*✅ Steam Market Alert!*\n\n"
        f"*Item:* {item_name}\n"
        f"*Price:* `{item_price}`\n"
        f"[Open on Steam]({item_url})"
    )

    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_notification": False,
        "disable_web_page_preview": True,
    }

    try:
        requests.post(url, json=data)
        print("Telegram notification sent.")
    except Exception as e:
        print("Telegram error:", e)

    
def sendDiscordNotification(item_name, item_price, item_url):
    name = str(item_name)
    price = str(item_price)
    url = str(item_url)

    embed = {
        "title": name,
        "url": url,
        "color": 3447003,
        "fields": [
            {
                "name": "Price",
                "value": price+"Euro",
                "inline": True
            },
            {
                "name": "Link",
                "value": f"[Open on Steam]({url})",
                "inline": False
            }
        ],
        "footer": {
            "text": "Steam Market Monitor"
        }
    }

    data = {
        "content": "@everyone",
        "embeds": [embed],
        "allowed_mentions": {
            "parse": ["everyone"]
        }
    }

    r = requests.post(DISCORD_WEBHOOK, json=data)
    print("Discord notification sent.")
    print("Status:", r.status_code, "Response:", r.text)
        
def PriceCheckLoop():
    print("✅ Price monitoring started. Checking every 2 minutes.\n")
    global no_change_counter
    while running:
        raw=FetchMarket()
        if raw:
            ParseData(raw)
        for remaining in range(FETCH_INTERVAL, 0, -1):
            if not running:
                break
            mins, secs = divmod(remaining, 60)
            timer = f"Next fetch in {mins:02d}:{secs:02d}"
            from_move = f"No change ({no_change_counter})" if no_change_counter > 0 else ""
            print(f"\r{timer}   {from_move}", end="", flush=True)
            time.sleep(1)
        print("\r" + " " * 40 + "\r", end="")  # clear line before next log
        
        
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