import threading
import random
import time
import requests
from mcstatus import JavaServer

# ===== CONFIG =====
API_URL = "https://web-production-d205.up.railway.app/log"
API_KEY = "secret123"

HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": API_KEY
}

THREADS = 120        # Safe for IP scanning
TIMEOUT = 2          # Fast timeout for dead IPs
PORT = 25565         # Default Minecraft port

cache = set()
lock = threading.Lock()
sent = 0
checked = 0


def random_public_ip():
    """Generate random PUBLIC IPv4 (skip useless private ranges)"""
    while True:
        a = random.randint(1, 223)
        b = random.randint(0, 255)
        c = random.randint(0, 255)
        d = random.randint(1, 254)

        # Skip private & reserved ranges (huge speed improvement)
        if (
            a == 10 or
            a == 127 or
            (a == 192 and b == 168) or
            (a == 172 and 16 <= b <= 31) or
            a >= 224
        ):
            continue

        return f"{a}.{b}.{c}.{d}:{PORT}"


def send_to_api(address, online, max_players, version):
    global sent
    try:
        payload = {
            "ip": address,
            "info": {
                "players": online,
                "max_players": max_players,
                "version": version,
                "source": "rl-ip-scanner"
            }
        }

        r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=10)

        if r.status_code == 200:
            sent += 1
            print(f"[ONLINE] {address} ({online}/{max_players})")
    except:
        pass  # Silent fail if API/railway sleeps


def worker():
    global checked

    while True:
        try:
            address = random_public_ip()
            checked += 1

            # Avoid re-checking same IPs
            with lock:
                if address in cache:
                    continue
                cache.add(address)

            try:
                server = JavaServer.lookup(address, timeout=TIMEOUT)
                status = server.status()
            except:
                continue  # Dead IP / closed port / timeout

            if not status or not status.players:
                continue

            online = status.players.online or 0
            max_players = status.players.max or 0
            version = status.version.name if status.version else "unknown"

            # ONLY log real active servers (with players)
            if online > 0 and max_players > 0:
                send_to_api(address, online, max_players, version)

        except:
            continue  # Never kill worker threads


def main():
    print("=== RL Minecraft Scanner (REAL IPs ONLY) ===")
    print("Mode: IPv4 scanning only")
    print("Domains: DISABLED")
    print("Minehut/Aternos: NOT scanned")
    print(f"Threads: {THREADS}")
    print(f"Timeout: {TIMEOUT}s\n")

    for _ in range(THREADS):
        threading.Thread(target=worker, daemon=True).start()

    while True:
        print(
            f"[STATS] Checked IPs: {checked} | "
            f"Online Found: {sent} | "
            f"Unique IPs: {len(cache)}"
        )
        time.sleep(5)


if __name__ == "__main__":
    main()
