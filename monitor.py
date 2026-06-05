import requests
import time
import os
from datetime import datetime
from collections import defaultdict

# =====================================================
# CONFIG
# =====================================================

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")

POLL_INTERVAL = 60
REDIS_TTL = 604800  # 7 Days

WALLETS = {
    "Orbt-maker Intent Operator": "0x09E8774Bc2c509A70441E5440b4CF524F4A764Ef",
    "OrbtExecutor v2": "0x39457F74251325F0dD14048480645d2165B0026e",
    "Filler_1inch_1": "0xFE377d0171ad1617Af848Ebd20dD59E09AF87Bd9",
    "Filler_OKX_1": "0x52A46016fDC6B260332191dD4b17F823CFa2cD51",
    "OrbtExecutor v1": "0x5ad05c158151248064A9DB38624000DDBa0eb6A1",
}

print("=" * 50)
print("BOT STARTED")
print("=" * 50)

# =====================================================
# FORMAT HELPERS
# =====================================================

def format_amount(value):
    try:
        return (
            f"{float(value):,.18f}"
            .rstrip("0")
            .rstrip(".")
        )
    except:
        return str(value)


def format_timestamp(timestamp):
    try:
        return datetime.utcfromtimestamp(
            int(timestamp)
        ).strftime("%d-%m-%Y %H:%M:%S UTC")
    except:
        return str(timestamp)

# =====================================================
# TELEGRAM
# =====================================================

def send_telegram(message):

    try:

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        r = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": message,
                "disable_web_page_preview": True
            },
            timeout=20
        )

        print("Telegram:", r.status_code)

    except Exception as e:

        print("Telegram Error:", str(e))

# =====================================================
# REDIS (UPSTASH REST)
# =====================================================

def redis_headers():
    return {
        "Authorization": f"Bearer {UPSTASH_TOKEN}"
    }


def redis_exists(key):

    try:

        r = requests.get(
            f"{UPSTASH_URL}/get/{key}",
            headers=redis_headers(),
            timeout=15
        )

        data = r.json()

        return data.get("result") is not None

    except Exception as e:

        print("Redis Exists Error:", str(e))
        return False


def redis_store(key):

    try:

        requests.get(
            f"{UPSTASH_URL}/setex/{key}/{REDIS_TTL}/1",
            headers=redis_headers(),
            timeout=15
        )

    except Exception as e:

        print("Redis Store Error:", str(e))

# =====================================================
# COINGECKO
# =====================================================

def get_eth_price():

    try:

        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd",
            timeout=20
        )

        data = r.json()

        return float(
            data["ethereum"]["usd"]
        )

    except Exception as e:

        print("CoinGecko Error:", str(e))

    return 0

# =====================================================
# ETHERSCAN ERC20
# =====================================================

def get_erc20_transactions(address):

    try:

        url = (
            "https://api.etherscan.io/v2/api"
            "?chainid=1"
            "&module=account"
            "&action=tokentx"
            f"&address={address}"
            "&page=1"
            "&offset=20"
            "&sort=desc"
            f"&apikey={ETHERSCAN_API_KEY}"
        )

        r = requests.get(
            url,
            timeout=30
        )

        data = r.json()

        if data.get("status") == "1":
            return data.get("result", [])

        print(data)

    except Exception as e:

        print("Etherscan Error:", str(e))

    return []

# =====================================================
# NORMALIZE TX
# =====================================================

def normalize_tx(tx, wallet_name):

    amount = (
        int(tx["value"])
        / (10 ** int(tx["tokenDecimal"]))
    )

    amount_str = format_amount(amount)

    return {
        "wallet": wallet_name,
        "hash": tx["hash"],
        "block": tx["blockNumber"],
        "timestamp": format_timestamp(
            tx["timeStamp"]
        ),
        "token_name": tx["tokenName"],
        "token_symbol": tx["tokenSymbol"],
        "amount": amount,
        "amount_str": amount_str,
        "from": tx["from"],
        "to": tx["to"],
        "contract": tx["contractAddress"],
        "gas_used": int(tx["gasUsed"]),
        "gas_price": int(tx["gasPrice"]),
        "confirmations": tx["confirmations"]
    }

# =====================================================
# DIRECTION
# =====================================================

def get_direction(tx, wallet_address):

    if tx["to"].lower() == wallet_address.lower():
        return "IN"

    return "OUT"

# =====================================================
# MAIN LOOP
# =====================================================

while True:

    try:

        print("=" * 50)
        print("CHECKING...")
        print("=" * 50)

        eth_price = get_eth_price()

        for wallet_name, wallet_address in WALLETS.items():

            print("Wallet:", wallet_name)

            txs = []

            erc20_txs = get_erc20_transactions(
                wallet_address
            )

            for tx in erc20_txs:

                tx_hash = tx["hash"]

                redis_key = (
                    f"{wallet_name}:{tx_hash}"
                )

                if redis_exists(redis_key):
                    continue

                redis_store(redis_key)

                txs.append(
                    normalize_tx(
                        tx,
                        wallet_name
                    )
                )

            if not txs:

                print("No New Transactions")
                continue

            grouped = defaultdict(list)

            for tx in txs:

                grouped[
                    tx["block"]
                ].append(tx)

            for block_number, block_txs in grouped.items():

                total_gas_eth = 0

                lines = []

                for tx in block_txs:

                    direction = get_direction(
                        tx,
                        wallet_address
                    )

                    gas_eth = (
                        tx["gas_used"]
                        * tx["gas_price"]
                    ) / 10**18

                    total_gas_eth += gas_eth

                    lines.append(
                        f"{direction} | "
                        f"{tx['token_symbol']} | "
                        f"{tx['amount_str']}"
                    )

                gas_eth_str = format_amount(
                    total_gas_eth
                )

                gas_usd = (
                    total_gas_eth
                    * eth_price
                )

                sample = block_txs[0]

                message = (
                    f"🚨 BLOCK ACTIVITY DETECTED\n\n"
                    f"Wallet:\n"
                    f"{wallet_name}\n\n"
                    f"Address:\n"
                    f"{wallet_address}\n\n"
                    f"Block:\n"
                    f"{block_number}\n\n"
                    f"Transactions:\n"
                    f"{len(block_txs)}\n\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"{chr(10).join(lines)}\n"
                    f"━━━━━━━━━━━━━━\n\n"
                    f"Gas Fee:\n"
                    f"{gas_eth_str} ETH\n"
                    f"~${gas_usd:,.2f}\n\n"
                    f"Timestamp UTC:\n"
                    f"{sample['timestamp']}\n\n"
                    f"Confirmations:\n"
                    f"{sample['confirmations']}\n\n"
                    f"https://etherscan.io/block/{block_number}"
                )

                send_telegram(message)

                print(
                    f"Alert Sent -> "
                    f"{wallet_name} "
                    f"Block {block_number}"
                )

        time.sleep(POLL_INTERVAL)

    except Exception as e:

        print(
            "MAIN LOOP ERROR:",
            str(e)
        )

        time.sleep(POLL_INTERVAL)
