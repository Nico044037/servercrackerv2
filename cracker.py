import threading
import random
import time
import requests
from mcstatus import JavaServer

# ===== CONFIG =====
API_URL = "https://web-production-d205.up.railway.app/log"  # NO double slash
API_KEY = "secret123"

THREADS = 80          # Optimal for network scanning
TIMEOUT = 2           # Never use 0 (causes hanging)
PORT = 25565
STATS_INTERVAL = 5

HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": API_KEY
}

# ===== STATE =====
checked_cache = set()
lock = threading.Lock()

checked = 0
sent = 0
alive_threads = 0


def random_public_ip():
    """Generate random public IPv4 (skip useless private ranges)"""
    while True:
        a = random.randint(1, 223)
        b = random.randint(0, 255)
        c = random.randint(0, 255)
        d = random.randint(1, 254)

        # Skip private/reserved ranges (major efficiency boost)
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
                "source": "rl-finder"
            }
        }

        r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=10)

        if r.status_code == 200:
            sent += 1
            print(f"[FOUND] {address} ({online}/{max_players})")
        elif r.status_code == 403:
            print("[ERROR] Invalid API Key!")
        else:
            print(f"[API ERROR] {r.status_code}")

    except requests.exceptions.RequestException:
        # Railway might sleep, don't kill threads
        pass


def worker():
    global checked, alive_threads

    alive_threads += 1

    while True:
        try:
            address = random_public_ip()

            # Avoid duplicate scans (huge efficiency gain)
            with lock:
                if address in checked_cache:
                    continue
                checked_cache.add(address)
                checked += 1

            try:
                server = JavaServer.lookup(address, timeout=TIMEOUT)
                status = server.status()
            except Exception:
                continue  # Dead IP / closed port / timeout

            if not status or not status.players:
                continue

            online = status.players.online or 0
            max_players = status.players.max or 0

            # Only send REAL active servers
            if online <= 0 or max_players <= 0:
                continue

            version = status.version.name if status.version else "unknown"
            send_to_api(address, online, max_players, version)

        except Exception:
            # Never let threads die
            continue


def stats_loop():
    while True:
        print(
            f"[STATS] Checked IPs: {checked} | "
            f"Found Online: {sent} | "
            f"Unique Targets: {len(checked_cache)} | "
            f"Threads: {THREADS}"
        )
        time.sleep(STATS_INTERVAL)


def main():
    print("=== RL Minecraft Finder (API Mode) ===")
    print("Mode: Real IP scanning only (no domains)")
    print(f"API Endpoint: {API_URL}")
    print(f"Threads: {THREADS}")
    print(f"Timeout: {TIMEOUT}s\n")

    # Start workers
    for _ in range(THREADS):
        t = threading.Thread(target=worker, daemon=True)
        t.start()

    # Start stats thread
    threading.Thread(target=stats_loop, daemon=True).start()

    # Keep main alive
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
