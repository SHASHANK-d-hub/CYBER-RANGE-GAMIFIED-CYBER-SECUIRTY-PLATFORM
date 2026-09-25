"""
CyberRange: Gamified Cybersecurity Training Platform
Red Team vs Blue Team simulation with real-time HUD dashboard
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import time
import subprocess
import random
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cyberrange_secret_2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# ─────────────────────────────────────────────
# GAME STATE
# ─────────────────────────────────────────────
game_state = {
    "health": 100,
    "red_score": 0,
    "blue_score": 0,
    "round": 1,
    "status": "active",
    "events": [],
    "victim_ip": "192.168.1.100",
    "red_ip": "192.168.1.10",
    "blue_ip": "192.168.1.20",
    "start_time": time.time(),
}

# ─────────────────────────────────────────────
# SCORE ENGINE
# ─────────────────────────────────────────────

def clamp_health(value):
    return max(0, min(100, value))


def add_event(team, action, delta, detail=""):
    ts = datetime.now().strftime("%H:%M:%S")
    event = {
        "id": int(time.time() * 1000),
        "timestamp": ts,
        "team": team,
        "action": action,
        "delta": delta,
        "detail": detail,
        "health_after": game_state["health"],
    }
    game_state["events"].insert(0, event)
    game_state["events"] = game_state["events"][:50]
    return event


def red_attack(action, points, detail=""):
    """Red Team attack — reduces system health."""
    if game_state["status"] != "active":
        return None
    game_state["health"] = clamp_health(game_state["health"] - points)
    game_state["red_score"] += points
    event = add_event("red", action, -points, detail)
    event["health_after"] = game_state["health"]
    if game_state["health"] <= 0:
        game_state["status"] = "red_wins"
    socketio.emit("game_update", build_payload(event))
    return event


def blue_defense(action, points, detail=""):
    """Blue Team defense — restores system health."""
    if game_state["status"] != "active":
        return None
    game_state["health"] = clamp_health(game_state["health"] + points)
    game_state["blue_score"] += points
    event = add_event("blue", action, +points, detail)
    event["health_after"] = game_state["health"]
    socketio.emit("game_update", build_payload(event))
    return event


def build_payload(latest_event=None):
    return {
        "health": game_state["health"],
        "red_score": game_state["red_score"],
        "blue_score": game_state["blue_score"],
        "status": game_state["status"],
        "round": game_state["round"],
        "events": game_state["events"][:20],
        "latest_event": latest_event,
        "elapsed": int(time.time() - game_state["start_time"]),
        "victim_ip": game_state["victim_ip"],
    }


# ─────────────────────────────────────────────
# ATTACK SIMULATION HELPERS
# ─────────────────────────────────────────────

def run_nmap_scan(target_ip):
    try:
        result = subprocess.run(
            ["nmap", "-T4", "--open", "-p", "22,80,443,8080,3306", target_ip],
            capture_output=True, text=True, timeout=30
        )
        open_ports = []
        for line in result.stdout.splitlines():
            if "/tcp" in line and "open" in line:
                open_ports.append(line.split("/")[0].strip())
        return open_ports, result.stdout
    except FileNotFoundError:
        ports = ["22", "80"]
        return ports, "[SIMULATED] nmap not installed — simulated open ports: 22, 80"
    except Exception as e:
        return [], str(e)


def run_hydra_brute(target_ip, username="testuser",
                    wordlist="/usr/share/wordlists/rockyou.txt"):
    try:
        result = subprocess.run(
            ["hydra", "-l", username, "-P", wordlist,
             f"ssh://{target_ip}", "-t", "4", "-f", "-q"],
            capture_output=True, text=True, timeout=60
        )
        success = "login:" in result.stdout.lower()
        return success, result.stdout[:500]
    except FileNotFoundError:
        success = random.random() < 0.3
        msg = f"[SIMULATED] hydra not installed. Result: {'SUCCESS — credentials found' if success else 'FAILED — no match'}"
        return success, msg
    except Exception as e:
        return False, str(e)


# ─────────────────────────────────────────────
# FLASK ROUTES
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def api_state():
    return jsonify(build_payload())


@app.route("/api/config", methods=["POST"])
def api_config():
    data = request.json or {}
    if "victim_ip" in data:
        game_state["victim_ip"] = data["victim_ip"]
    if "red_ip" in data:
        game_state["red_ip"] = data["red_ip"]
    if "blue_ip" in data:
        game_state["blue_ip"] = data["blue_ip"]
    return jsonify({"status": "updated", "config": {
        "victim_ip": game_state["victim_ip"],
        "red_ip": game_state["red_ip"],
        "blue_ip": game_state["blue_ip"],
    }})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    game_state.update({
        "health": 100,
        "red_score": 0,
        "blue_score": 0,
        "round": game_state["round"] + 1,
        "status": "active",
        "events": [],
        "start_time": time.time(),
    })
    socketio.emit("game_update", build_payload())
    return jsonify({"status": "reset", "round": game_state["round"]})


# ─── RED TEAM ENDPOINTS ───────────────────────

@app.route("/api/red/portscan", methods=["POST"])
def api_portscan():
    data = request.json or {}
    target = data.get("target", game_state["victim_ip"])
    ports, raw = run_nmap_scan(target)
    detail = f"Found ports: {', '.join(ports) if ports else 'none'} on {target}"
    event = red_attack("Port Scan (nmap)", 5, detail)
    return jsonify({"event": event, "ports": ports, "raw": raw[:300]})


@app.route("/api/red/bruteforce", methods=["POST"])
def api_bruteforce():
    data = request.json or {}
    target = data.get("target", game_state["victim_ip"])
    username = data.get("username", "testuser")
    success, raw = run_hydra_brute(target, username)
    if success:
        event = red_attack("SSH Brute Force — SUCCESS", 20,
                           f"Credentials cracked for {username}@{target}")
    else:
        event = red_attack("SSH Brute Force — FAILED", 2,
                           f"No match for {username}@{target}")
    return jsonify({"event": event, "success": success, "raw": raw})


@app.route("/api/red/webapp", methods=["POST"])
def api_webapp():
    data = request.json or {}
    target = data.get("target", game_state["victim_ip"])
    event = red_attack("Web App Exploit (SQLi)", 10,
                       f"SQL injection attempt on http://{target}/login")
    return jsonify({"event": event})


@app.route("/api/red/privesc", methods=["POST"])
def api_privesc():
    event = red_attack("Privilege Escalation", 15,
                       "Attempted sudo/SUID exploit on victim machine")
    return jsonify({"event": event})


@app.route("/api/red/dos", methods=["POST"])
def api_dos():
    event = red_attack("Denial of Service", 8,
                       "Flood attack on victim web server port 80")
    return jsonify({"event": event})


# ─── BLUE TEAM ENDPOINTS ──────────────────────

@app.route("/api/blue/detect", methods=["POST"])
def api_detect():
    data = request.json or {}
    detail = data.get("detail", "Anomalous traffic pattern detected via IDS")
    event = blue_defense("Attack Detected", 10, detail)
    return jsonify({"event": event})


@app.route("/api/blue/password_reset", methods=["POST"])
def api_password_reset():
    event = blue_defense("Password Reset", 20,
                         "Rotated SSH credentials on victim machine")
    return jsonify({"event": event})


@app.route("/api/blue/block_ip", methods=["POST"])
def api_block_ip():
    data = request.json or {}
    ip = data.get("ip", game_state["red_ip"])
    event = blue_defense("IP Blocked (iptables)", 15,
                         f"Blocked {ip} via firewall rule")
    return jsonify({"event": event})


@app.route("/api/blue/patch", methods=["POST"])
def api_patch():
    event = blue_defense("System Patch Applied", 20,
                         "Patched vulnerable service on victim machine")
    return jsonify({"event": event})


@app.route("/api/blue/honeypot", methods=["POST"])
def api_honeypot():
    event = blue_defense("Honeypot Deployed", 10,
                         "Fake SSH service deployed to trap attacker")
    return jsonify({"event": event})


@app.route("/api/blue/wazuh_alert", methods=["POST"])
def api_wazuh():
    """Wazuh SIEM webhook — auto-triggers blue defense on real alerts."""
    data = request.json or {}
    rule_desc = data.get("rule", {}).get("description", "Unknown Wazuh alert")
    level = int(data.get("rule", {}).get("level", 5))
    points = min(level * 2, 20)
    event = blue_defense(f"Wazuh Alert (Level {level})", points, rule_desc)
    return jsonify({"event": event})


# ─────────────────────────────────────────────
# WEBSOCKET
# ─────────────────────────────────────────────

@socketio.on("connect")
def handle_connect():
    emit("game_update", build_payload())


@socketio.on("request_state")
def handle_request_state():
    emit("game_update", build_payload())


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════╗
║        CYBERRANGE — SERVER ONLINE                ║
║   Dashboard: http://0.0.0.0:5000                 ║
║   Red  API:  POST /api/red/portscan              ║
║              POST /api/red/bruteforce            ║
║   Blue API:  POST /api/blue/detect               ║
║              POST /api/blue/password_reset       ║
╚══════════════════════════════════════════════════╝
    """)
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)