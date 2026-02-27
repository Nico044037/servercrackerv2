import threading
import random
import time
import requests
from mcstatus import JavaServer

# ===== CONFIG =====
API_URL = "https://web-production-d205.up.railway.app/log"
API_KEY = "secret123"

THREADS = 120        # Faster but still stable
TIMEOUT = 2          # Never 0 (prevents hanging)
STATS_INTERVAL = 5

HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": API_KEY
}

# ONLY ATERNOS (as requested)
ATERnos_DOMAINS = ["aternos.me", "aternos.org"]

COMMON_NAMES = [
    "play", "mc", "survival", "smp", "pvp", "lobby", "hub",
    "skyblock", "bedwars", "lifesteal", "craft", "mine",
    "vanilla", "network", "earth", "fun", "official",
    "anarchy", "minigames", "world", "creative"
]

PREFIXES = [
    "nova", "zen", "astro", "pixel", "void", "lunar",
    "apex", "fusion", "quantum", "echo", "vortex",
    "stellar", "nebula", "orbit", "cosmic"
]

SUFFIXES = [
    "mc", "smp", "pvp", "network", "craft", "realm",
    "world", "server", "hub", "survival", "online", "live"
]

# ===== STATE =====
cache = set()
lock = threading.Lock()
checked = 0
sent = 0


def generate_aternos_name():
    """High-efficiency Aternos name generator"""
    style = random.randint(0, 5)

    if style == 0:
        return random.choice(COMMON_NAMES)
    elif style == 1:
        return f"{random.choice(COMMON_NAMES)}{random.randint(1, 999)}"
    elif style == 2:
        return f"{random.choice(PREFIXES)}{random.choice(SUFFIXES)}"
    elif style == 3:
        return f"play{random.choice(COMMON_NAMES)}"
    elif style == 4:
        return f"{random.choice(PREFIXES)}{random.choice(COMMON_NAMES)}"
    else:
        return f"{random.choice(COMMON_NAMES)}{random.choice(SUFFIXES)}"


def generate_aternos_address():
    """ONLY generates Aternos servers (fast focus scanning)"""
    name = generate_aternos_name()
    domain = random.choice(ATERnos_DOMAINS)
    return f"{name}.{domain}".lower()


def send_to_api(address, online, max_players, version):
    global sent
    try:
        payload = {
            "ip": address,
            "info": {
                "players": online,
                "max_players": max_players,
                "version": version,
                "source": "aternos-fast-finder"
            }
        }

        r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=10)

        if r.status_code == 200:
            sent += 1
            print(f"[FOUND] {address} ({online}/{max_players})")

    except requests.exceptions.RequestException:
        # Railway sleep / network hiccup safe
        pass


def worker():
    global checked

    while True:
        try:
            address = generate_aternos_address()

            # Prevent duplicate checks (BIG speed gain)
            with lock:
                if address in cache:
                    continue
                cache.add(address)
                checked += 1

            try:
                server = JavaServer.lookup(address, timeout=TIMEOUT)
                status = server.status()
            except Exception:
                continue  # dead/offline server

            if not status or not status.players:
                continue

            online = status.players.online or 0
            max_players = status.players.max or 0
            version = status.version.name if status.version else "unknown"

            # Only log real servers (faster API filtering)
            if max_players > 0:
                send_to_api(address, online, max_players, version)

        except Exception:
            # Never let threads die (important for long runs)
            continue


def stats_loop():
    while True:
        print(
            f"[STATS] Checked: {checked} | "
            f"Found: {sent} | "
            f"Unique Generated: {len(cache)} | "
            f"Mode: Aternos Only"
        )
        time.sleep(STATS_INTERVAL)


def main():
    print("=== FAST ATERNOS ONLY FINDER ===")
    print("RL Scanning: DISABLED")
    print("Minehut: DISABLED")
    print("Domains: aternos.me + aternos.org ONLY")
    print(f"Threads: {THREADS}")
    print(f"Timeout: {TIMEOUT}s\n")

    # Start workers
    for _ in range(THREADS):
        threading.Thread(target=worker, daemon=True).start()

    # Stats thread
    threading.Thread(target=stats_loop, daemon=True).start()

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
