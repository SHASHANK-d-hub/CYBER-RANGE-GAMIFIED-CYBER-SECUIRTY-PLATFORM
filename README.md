# CyberRange — Gamified Cybersecurity Training Platform

A Counter-Strike-inspired cyber battle simulator with real-time HUD dashboard.
Red Team attacks, Blue Team defends, a live scoreboard tracks everything.

---

## Network Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   RED TEAM      │     │     VICTIM      │     │   BLUE TEAM     │
│  Kali Linux     │────▶│  Ubuntu         │◀────│  Ubuntu         │
│  192.168.1.10   │     │  192.168.1.100  │     │  192.168.1.20   │
│                 │     │  SSH + Apache   │     │  Flask Dashboard│
│  nmap, hydra    │     │  testuser:pw123 │     │  :5000          │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## Quick Start

### 1. Blue Team Machine — Start Dashboard

```bash
# Install dependencies
pip3 install -r requirements.txt

# Start the scoreboard server
python3 app.py
# Dashboard: http://192.168.1.20:5000
```

### 2. Victim Machine — Setup Target

```bash
# Run setup script (Ubuntu)
chmod +x scripts/setup_victim.sh
sudo bash scripts/setup_victim.sh
# Creates: testuser / password123 (intentionally weak)
# Starts:  SSH on :22, Apache on :80
```

### 3. Red Team Machine — Launch Attacks (Kali Linux)

```bash
# Install attack tools
sudo apt install nmap hydra hping3

# Port scan
python3 scripts/red_attacks.py --target 192.168.1.100 --attack portscan

# SSH brute-force
python3 scripts/red_attacks.py --target 192.168.1.100 --attack bruteforce

# Web app exploit
python3 scripts/red_attacks.py --target 192.168.1.100 --attack webapp

# Run all attacks
python3 scripts/red_attacks.py --target 192.168.1.100 --attack all \
  --scoreboard http://192.168.1.20:5000
```

### 4. Blue Team Console — Defend

```bash
# Detect attacks (analyzes auth logs)
python3 scripts/blue_defense.py --action detect --victim 192.168.1.100

# Block attacker IP
python3 scripts/blue_defense.py --action block_ip --attacker 192.168.1.10

# Reset compromised password
python3 scripts/blue_defense.py --action password_reset --user testuser

# Apply SSH hardening
python3 scripts/blue_defense.py --action patch

# Deploy honeypot
python3 scripts/blue_defense.py --action honeypot
```

---

## Game Mechanics

| Action | Team | HP Change |
|--------|------|-----------|
| Port Scan (nmap) | Red | −5 |
| SSH Brute Force (failed) | Red | −2 |
| SSH Brute Force (success) | Red | −20 |
| Web App Exploit | Red | −10 |
| Privilege Escalation | Red | −15 |
| Denial of Service | Red | −8 |
| Attack Detected | Blue | +10 |
| Password Reset | Blue | +20 |
| Block IP | Blue | +15 |
| Security Patch | Blue | +20 |
| Deploy Honeypot | Blue | +10 |
| Wazuh SIEM Alert (auto) | Blue | +2×level |

Health stays between 0 and 100. Red wins when health hits 0.

---

## API Reference

### Red Team Endpoints
```
POST /api/red/portscan      {"target": "192.168.1.100"}
POST /api/red/bruteforce    {"target": "...", "username": "testuser"}
POST /api/red/webapp        {"target": "192.168.1.100"}
POST /api/red/privesc
POST /api/red/dos
```

### Blue Team Endpoints
```
POST /api/blue/detect           {"detail": "custom message"}
POST /api/blue/password_reset
POST /api/blue/block_ip         {"ip": "192.168.1.10"}
POST /api/blue/patch
POST /api/blue/honeypot
POST /api/blue/wazuh_alert      {"rule": {"level": 10, "description": "..."}}
```

### Game Control
```
GET  /api/state     — current game state (JSON)
POST /api/reset     — start new round
POST /api/config    {"victim_ip": "...", "red_ip": "...", "blue_ip": "..."}
```

---

## Wazuh SIEM Integration (Automation)

Automatically award Blue Team points when Wazuh detects attacks:

1. Install Wazuh agent on victim machine
2. Run `python3 scripts/blue_defense.py --action wazuh_setup`
3. Follow the instructions to add the active-response config
4. Wazuh will POST to `/api/blue/wazuh_alert` on every alert

---

## Project Structure

```
cyberrange/
├── app.py                      # Flask + SocketIO backend
├── requirements.txt
├── templates/
│   └── index.html              # Gaming HUD dashboard
├── static/
│   ├── css/                    # (optional custom CSS)
│   └── js/                     # (optional extra scripts)
└── scripts/
    ├── red_attacks.py           # Red team attack console
    ├── blue_defense.py          # Blue team defense console
    └── setup_victim.sh          # Victim machine setup
```

---

## Safety & Ethics

- **Only attack machines you own or have explicit written permission to test**
- Keep all machines on an isolated private network (VMware host-only, VirtualBox internal, etc.)
- Never run this on a public cloud instance without strict security group rules
- The victim setup script intentionally creates vulnerabilities — never run it on production

---

## Extending the Platform

- **Add Snort/Suricata IDS** → pipe alerts to `/api/blue/detect`
- **Add Metasploit** → report exploits via `/api/red/privesc`
- **Add scoring persistence** → swap `game_state` dict for SQLite
- **Add team authentication** → add JWT to API endpoints
- **Multi-round tournament mode** → track wins per round in DB
  3301
  paris,china
