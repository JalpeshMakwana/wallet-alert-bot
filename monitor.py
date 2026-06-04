import requests
import time
import os
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
REDIS_TTL = 604800  # 7 days

WALLETS = {
    "Orbt-maker Intent Operator": "0x09E8774Bc2c509A70441E5440b4CF524F4A764Ef",
    "OrbtExecutor v2": "0x39457F74251325F0dD14048480645d2165B0026e",
    "Filler_1inch_1": "0xFE377d0171ad1617Af848Ebd20dD59E09AF87Bd9",
    "Filler_OKX_1": "0x52A46016fDC6B260332191dD4b17F823CFa2cD51",
}

print("===================================")
print("BOT STARTED")
print("===================================")
print("ETHERSCAN:", bool(ETHERSCAN_API_KEY))
print("BOT:", bool(BOT_TOKEN))
print("CHAT:", bool(CHAT_ID))
print("REDIS URL:", bool(UPSTASH_URL))
print("REDIS TOKEN:", bool(UPSTASH_TOKEN))
print("===================================")


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
        print("Telegram Error:", e)


# =====================================================
# REDIS (UPSTASH REST)
# =====================================================

def redis_headers():
    return {
        "Authorization": f"Bearer {UPSTASH_TOKEN}"
    }


def redis_exists(tx_hash):
    try:
        r = requests.get(
            f"{UPSTASH_URL}/get/processed_tx:{tx_hash}",
            headers=redis_headers(),
            timeout=15
        )

        data = r.json()

        return data.get("result") is not None

    except Exception as e:
        print("Redis exists error:", e)
        return False


def redis_store(tx_hash):
    try:
        requests.get(
            f"{UPSTASH_URL}/setex/processed_tx:{tx_hash}/{REDIS_TTL}/1",
            headers=redis_headers(),
            timeout=15
        )

    except Exception as e:
        print("Redis store error:", e)


# =====================================================
# ETH PRICE
# =====================================================

def get_eth_price():
    try:

        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd",
            timeout=20
        )

        data = r.json()

        return float(data["ethereum"]["usd"])

    except Exception as e:
        print("CoinGecko Error:", e)

    return 0


# =====================================================
# ETHERSCAN
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

        r = requests.get(url, timeout=30)

        data = r.json()

        if data.get("status") == "1":
            return data.get("result", [])

    except Exception as e:
        print("ERC20 Error:", e)

    return []


def get_eth_transactions(address):

    try:

        url = (
            "https://api.etherscan.io/v2/api"
            "?chainid=1"
            "&module=account"
            "&action=txlist"
            f"&address={address}"
            "&page=1"
            "&offset=20"
            "&sort=desc"
            f"&apikey={ETHERSCAN_API_KEY}"
        )

        r = requests.get(url, timeout=30)

        data = r.json()

        if data.get("status") == "1":
            return data.get("result", [])

    except Exception as e:
        print("ETH Error:", e)

    return []


# =====================================================
# HELPERS
# =====================================================

def normalize_erc20(tx, wallet):

    amount = (
        int(tx["value"])
        / (10 ** int(tx["tokenDecimal"]))
    )

    return {
        "hash": tx["hash"],
        "block": tx["blockNumber"],
        "timestamp": tx["timeStamp"],
        "wallet": wallet,
        "token": tx["tokenSymbol"],
        "token_name": tx["tokenName"],
        "amount": amount,
        "from": tx["from"],
        "to": tx["to"],
        "contract": tx["contractAddress"],
        "gas_used": int(tx["gasUsed"]),
        "gas_price": int(tx["gasPrice"]),
        "confirmations": tx["confirmations"],
        "type": "ERC20"
    }


def normalize_eth(tx, wallet):

    amount = int(tx["value"]) / 10**18

    return {
        "hash": tx["hash"],
        "block": tx["blockNumber"],
        "timestamp": tx["timeStamp"],
        "wallet": wallet,
        "token": "ETH",
        "token_name": "Ethereum",
        "amount": amount,
        "from": tx["from"],
        "to": tx["to"],
        "contract": "",
        "gas_used": int(tx["gasUsed"]),
        "gas_price": int(tx["gasPrice"]),
        "confirmations": tx["confirmations"],
        "type": "ETH"
    }


def tx_direction(tx, wallet_address):

    if tx["to"].lower() == wallet_address.lower():
        return "IN"

    return "OUT"


# =====================================================
# MAIN
# =====================================================

while True:

    try:

        print("===================================")
        print("CHECKING...")
        print("===================================")

        eth_price = get_eth_price()

        for wallet_name, wallet_address in WALLETS.items():

            print("Wallet:", wallet_name)

            txs = []

            erc20 = get_erc20_transactions(wallet_address)
            eth = get_eth_transactions(wallet_address)

            for tx in erc20:
                txs.append(
                    normalize_erc20(tx, wallet_name)
                )

            for tx in eth:
                txs.append(
                    normalize_eth(tx, wallet_name)
                )

            new_txs = []

            for tx in txs:

                if redis_exists(tx["hash"]):
                    continue

                redis_store(tx["hash"])
                new_txs.append(tx)

            if not new_txs:
                print("No New TX")
                continue

            grouped = defaultdict(list)

            for tx in new_txs:
                grouped[tx["block"]].append(tx)

            for block_number, block_txs in grouped.items():

                total_gas_eth = 0

                lines = []

                for tx in block_txs:

                    direction = tx_direction(
                        tx,
                        wallet_address
                    )

                    gas_eth = (
                        tx["gas_used"]
                        * tx["gas_price"]
                    ) / 10**18

                    total_gas_eth += gas_eth

                    lines.append(
                        f"{direction} | {tx['token']} | {tx['amount']:.6f}"
                    )

                gas_usd = total_gas_eth * eth_price

                sample = block_txs[0]

                msg = (
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
                    f"{total_gas_eth:.6f} ETH\n"
                    f"~${gas_usd:.2f}\n\n"
                    f"Timestamp UTC:\n"
                    f"{sample['timestamp']}\n\n"
                    f"Confirmations:\n"
                    f"{sample['confirmations']}\n\n"
                    f"https://etherscan.io/block/{block_number}"
                )

                send_telegram(msg)

                print(
                    f"Alert Sent -> "
                    f"{wallet_name} "
                    f"Block {block_number}"
                )

        time.sleep(POLL_INTERVAL)

    except Exception as e:

        print("MAIN LOOP ERROR:", e)

        time.sleep(POLL_INTERVAL)
