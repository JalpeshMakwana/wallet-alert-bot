import requests
import time
import os

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

ADDRESS = "0x5ad05c158151248064a9db38624000ddba0eb6a1"

LAST_HASH = None

print("Bot started...")
print("API KEY FOUND:", bool(ETHERSCAN_API_KEY))
print("BOT FOUND:", bool(BOT_TOKEN))
print("CHAT FOUND:", bool(CHAT_ID))

send("✅ Bot Online & Monitoring ERC20 Transactions")


def send(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        r = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": msg
            },
            timeout=15
        )

        print("Telegram Status:", r.status_code)
        print("Telegram Response:", r.text)

    except Exception as e:
        print("Telegram Error:", str(e))


def get_latest_tx():
    try:
        url = (
    "https://api.etherscan.io/v2/api"
    "?chainid=1"
    "&module=account"
    "&action=tokentx"
    f"&address={ADDRESS}"
    "&page=1"
    "&offset=1"
    "&sort=desc"
    f"&apikey={ETHERSCAN_API_KEY}"
)

        r = requests.get(url, timeout=20)

        print("ETHERSCAN STATUS:", r.status_code)

        data = r.json()

        print("ETHERSCAN RESPONSE:", data)

        if (
            data.get("status") == "1"
            and len(data.get("result", [])) > 0
        ):
            return data["result"][0]

    except Exception as e:
        print("Etherscan Error:", str(e))

    return None


while True:
    try:
        print("Checking transactions...")

        tx = get_latest_tx()

        if tx:

            current_hash = tx["hash"]

            if LAST_HASH is None:
                LAST_HASH = current_hash
                print("Initial transaction stored:", current_hash)

            elif current_hash != LAST_HASH:

                amount = (
                    int(tx["value"])
                    / (10 ** int(tx["tokenDecimal"]))
                )

                message = (
                    f"🚨 NEW ERC20 TRANSFER\n\n"
                    f"Token: {tx['tokenSymbol']}\n"
                    f"Amount: {amount}\n\n"
                    f"From:\n{tx['from']}\n\n"
                    f"To:\n{tx['to']}\n\n"
                    f"https://etherscan.io/tx/{current_hash}"
                )

                send(message)

                LAST_HASH = current_hash

                print("Alert Sent")

            else:
                print("No New Transaction")

        else:
            print("No Transaction Found")

        time.sleep(30)

    except Exception as e:
        print("MAIN LOOP ERROR:", str(e))
        time.sleep(30)
