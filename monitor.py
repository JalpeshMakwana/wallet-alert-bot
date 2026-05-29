import requests
import time
import os

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
ADDRESS = "0x5ad05c158151248064a9db38624000ddba0eb6a1"

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

LAST_TX_FILE = "last_tx.txt"

def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

def get_latest_tx():
    url = (
        f"https://api.etherscan.io/api"
        f"?module=account"
        f"&action=tokentx"
        f"&address={ADDRESS}"
        f"&page=1"
        f"&offset=1"
        f"&sort=desc"
        f"&apikey={ETHERSCAN_API_KEY}"
    )

    r = requests.get(url).json()

    if r["status"] == "1":
        return r["result"][0]

    return None

def load_last_tx():
    try:
        with open(LAST_TX_FILE, "r") as f:
            return f.read().strip()
    except:
        return ""

def save_last_tx(txhash):
    with open(LAST_TX_FILE, "w") as f:
        f.write(txhash)

print("Bot started...")

while True:
    try:
        tx = get_latest_tx()

        if tx:
            current_hash = tx["hash"]
            saved_hash = load_last_tx()

            if current_hash != saved_hash:

                message = f"""
🚨 NEW ERC20 TRANSFER

Token: {tx['tokenSymbol']}
Amount: {tx['value']}

From:
{tx['from']}

To:
{tx['to']}

https://etherscan.io/tx/{current_hash}
"""

                send(message)

                save_last_tx(current_hash)

                print("New alert sent!")

        time.sleep(30)

    except Exception as e:
        print("Error:", e)
        time.sleep(30)
