import requests
import time
import os

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
ADDRESS = "0x5ad05c158151248064a9db38624000ddba0eb6a1"

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

last_tx = ""

def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def get_tx():
    url = f"https://api.etherscan.io/api?module=account&action=tokentx&address={ADDRESS}&page=1&offset=1&sort=desc&apikey={ETHERSCAN_API_KEY}"
    r = requests.get(url).json()
    return r["result"][0] if r["status"] == "1" else None

print("Bot started...")

while True:
    try:
        tx = get_tx()

        if tx:
            if tx["hash"] != last_tx:
                last_tx = tx["hash"]

                message = f"""
🚨 NEW ERC-20 TXN

Token: {tx['tokenSymbol']}
Amount: {tx['value']}
From: {tx['from']}
To: {tx['to']}

https://etherscan.io/tx/{tx['hash']}
"""

                send(message)
                print("Alert sent!")

        time.sleep(30)

    except Exception as e:
        print("Error:", e)
        time.sleep(30)
