import threading
import random
import time
import requests
from mcstatus import JavaServer

# ===== CONFIG =====
API_URL = "https://web-production-d205.up.railway.app/log"
API_KEY = "secret123"

THREADS = 100        # Fast but stable
TIMEOUT = 2          # NEVER use 0 (causes freezes)
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

# Reuse HTTP connection (faster than new request each time)
session = requests.Session()


def generate_name():
    """Efficient random Aternos-style name generator"""
    style = random.randint(0, 5)

    if style == 0:
        return random.choice(COMMON_NAMES)
    elif style == 1:
        return f"{random.choice(COMMON_NAMES)}{random.randint(1,999)}"
    elif style == 2:
        return f"{random.choice(PREFIXES)}{random.choice(SUFFIXES)}"
    elif style == 3:
        return f"play{random.choice(COMMON_NAMES)}"
    elif style == 4:
        return f"{random.choice(PREFIXES)}{random.choice(COMMON_NAMES)}"
    else:
        return f"{random.choice(COMMON_NAMES)}{random.choice(SUFFIXES)}"


def generate_aternos_address():
    """ONLY generates Aternos domains (no RL, no minehut)"""
    domain = random.choice(ATERnos_DOMAINS)
    return f"{generate_name()}.{domain}".lower()


def send_to_api(address, online, max_players, version):
    global sent
    try:
        payload = {
            "ip": address,
            "info": {
                "players": online,
                "max_players": max_players,
                "version": version,
                "source": "aternos-finder"
            }
        }

        r = session.post(API_URL, json=payload, headers=HEADERS, timeout=10)

        if r.status_code == 200:
            sent += 1
            print(f"[FOUND] {address} ({online}/{max_players})")
        elif r.status_code == 403:
            print("[ERROR] Invalid API Key")

    except requests.exceptions.RequestException:
        # Handles Railway sleep / network hiccups
        pass


def worker():
    global checked

    while True:
        try:
            address = generate_aternos_address()

            # Skip duplicates instantly (major speed gain)
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

            if not status:
                continue

            players = status.players
            online = players.online if players else 0
            max_players = players.max if players else 0
            version = status.version.name if status.version else "unknown"

            # Faster logging mode:
            # Logs ALL real Aternos servers (even 0 players)
            if max_players > 0:
                send_to_api(address, online, max_players, version)

        except Exception:
            # Never let threads die
            continue


def stats_loop():
    while True:
        print(
            f"[STATS] Checked: {checked} | "
            f"Sent to API: {sent} | "
            f"Unique Generated: {len(cache)} | "
            f"Mode: Aternos Only"
        )
        time.sleep(STATS_INTERVAL)


def main():
    print("=== FAST ATERNOS FINDER ===")
    print("RL Scanning: DISABLED")
    print("Minehut: DISABLED")
    print("Domains: aternos.me + aternos.org ONLY")
    print(f"Threads: {THREADS}")
    print(f"Timeout: {TIMEOUT}s\n")

    # Start workers
    for _ in range(THREADS):
        threading.Thread(target=worker, daemon=True).start()

    # Start stats thread
    threading.Thread(target=stats_loop, daemon=True).start()

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
