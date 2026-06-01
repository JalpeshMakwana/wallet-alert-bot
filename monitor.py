import requests
import time
import os

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ADDRESS = "0x5ad05c158151248064a9db38624000ddba0eb6a1"

LAST_HASH = ""

print("Bot started...")
print("API KEY FOUND:", bool(ETHERSCAN_API_KEY))
print("BOT FOUND:", bool(BOT_TOKEN))
print("CHAT FOUND:", bool(CHAT_ID))


def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    r = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": msg
        }
    )

    print("Telegram:", r.status_code)


def get_latest_tx():
    url = (
        "https://api.etherscan.io/api"
        f"?module=account"
        f"&action=tokentx"
        f"&address={ADDRESS}"
        f"&page=1"
        f"&offset=1"
        f"&sort=desc"
        f"&apikey={ETHERSCAN_API_KEY}"
    )

    r = requests.get(url)

    print("ETHERSCAN STATUS:", r.status_code)

    data = r.json()

    print("ETHERSCAN RESPONSE:", data)

    if (
        data.get("status") == "1"
        and len(data.get("result", [])) > 0
    ):
        return data["result"][0]

    return None


while True:

    try:

        print("Checking...")

        tx = get_latest_tx()

        if tx:

            current_hash = tx["hash"]

            global LAST_HASH

            if LAST_HASH == "":
                LAST_HASH = current_hash

            elif current_hash != LAST_HASH:

                amount = (
                    int(tx["value"])
                    / (10 ** int(tx["tokenDecimal"]))
                )

                send(
                    f"🚨 ERC20 Transfer\n\n"
                    f"Token: {tx['tokenSymbol']}\n"
                    f"Amount: {amount}\n"
                    f"TX:\nhttps://etherscan.io/tx/{current_hash}"
                )

                LAST_HASH = current_hash

                print("Alert Sent")

            else:

                print("No New TX")

        else:

            print("No TX Found")

        time.sleep(30)

    except Exception as e:

        print("ERROR:", str(e))

        time.sleep(30)
