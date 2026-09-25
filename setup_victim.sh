#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# CyberRange — Victim Machine Setup Script
# Run this on the Ubuntu victim machine (192.168.1.100)
# WARNING: This intentionally creates a WEAK/VULNERABLE setup
#          for training purposes ONLY. Never run on production.
# ═══════════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════╗"
echo "║   CYBERRANGE — VICTIM MACHINE SETUP              ║"
echo "║   WARNING: Intentionally vulnerable setup        ║"
echo "╚══════════════════════════════════════════════════╝"
echo -e "${NC}"

# ─── 1. UPDATE ────────────────────────────────────────────────
echo -e "${GREEN}[*] Updating package lists…${NC}"
sudo apt update -q

# ─── 2. INSTALL OPENSSH ───────────────────────────────────────
echo -e "${GREEN}[*] Installing OpenSSH server…${NC}"
sudo apt install -y openssh-server

# Configure SSH to allow password auth (intentionally weak)
sudo tee /etc/ssh/sshd_config.d/cyberrange.conf > /dev/null << 'EOF'
# CyberRange training config — intentionally permissive
PasswordAuthentication yes
PermitRootLogin no 
MaxAuthTries 100
LoginGraceTime 120
EOF

sudo systemctl enable ssh
sudo systemctl restart ssh
echo -e "${GREEN}[+] SSH server running${NC}"

# ─── 3. CREATE WEAK TEST USER ─────────────────────────────────
echo -e "${GREEN}[*] Creating weak test user 'testuser'…${NC}"
if id "testuser" &>/dev/null; then
    echo "    testuser already exists — resetting password"
else
    sudo useradd -m -s /bin/bash testuser
    echo "    Created user: testuser"
fi

# Set intentionally weak password for training
echo "testuser:password123" | sudo chpasswd
echo -e "${GREEN}[+] testuser created with password: password123${NC}"
echo -e "${RED}[!] INTENTIONALLY WEAK — for training only${NC}"

# ─── 4. INSTALL APACHE WEB SERVER ─────────────────────────────
echo -e "${GREEN}[*] Installing Apache web server…${NC}"
sudo apt install -y apache2

# Create a fake vulnerable login page
sudo tee /var/www/html/login.php > /dev/null << 'EOF'
<?php
// CyberRange training target — intentionally vulnerable to SQLi
$db = new SQLite3('/var/www/html/users.db');
$db->exec("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)");
$db->exec("INSERT OR IGNORE INTO users VALUES (1, 'admin', 'admin123')");

$error = "";
if ($_POST) {
    $user = $_POST['username'] ?? '';
    $pass = $_POST['password'] ?? '';
    // INTENTIONALLY VULNERABLE to SQL injection (training only)
    $q = "SELECT * FROM users WHERE username='$user' AND password='$pass'";
    $res = $db->query($q);
    if ($res && $res->fetchArray()) {
        echo "<h2 style='color:red'>ACCESS GRANTED — SYSTEM COMPROMISED</h2>";
        exit;
    } else {
        $error = "Invalid credentials";
    }
}
?>
<!DOCTYPE html>
<html>
<head><title>CyberRange Target — Login</title>
<style>body{background:#111;color:#eee;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh;}</style>
</head>
<body>
<form method="POST">
    <h2>System Login</h2>
    <?php if($error) echo "<p style='color:red'>$error</p>"; ?>
    <input type="text" name="username" placeholder="username"><br><br>
    <input type="password" name="password" placeholder="password"><br><br>
    <button type="submit">Login</button>
</form>
</body>
</html>
EOF

sudo apt install -y php libapache2-mod-php php-sqlite3
sudo a2enmod php*
sudo systemctl restart apache2
echo -e "${GREEN}[+] Apache + vulnerable login page running at http://$(hostname -I | awk '{print $1}')/login.php${NC}"

# ─── 5. CONFIGURE FIREWALL (ufw) ──────────────────────────────
echo -e "${GREEN}[*] Setting up UFW firewall…${NC}"
sudo apt install -y ufw
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw --force enable
echo -e "${GREEN}[+] UFW configured${NC}"

# ─── 6. INSTALL SYSLOG / AUDITD ───────────────────────────────
echo -e "${GREEN}[*] Enabling system logging…${NC}"
sudo apt install -y auditd
sudo systemctl enable auditd
sudo systemctl start auditd
# Log all auth events
sudo auditctl -w /var/log/auth.log -p rwxa -k auth_events 2>/dev/null || true
echo -e "${GREEN}[+] auditd running${NC}"

# ─── 7. DISPLAY SUMMARY ───────────────────────────────────────
MY_IP=$(hostname -I | awk '{print $1}')
echo ""
echo -e "${CYAN}════════════════════════════════════════════════════"
echo "  VICTIM MACHINE SETUP COMPLETE"
echo "════════════════════════════════════════════════════"
echo -e "  IP Address:     ${MY_IP}"
echo "  SSH Port:       22"
echo "  HTTP Port:      80"
echo ""
echo "  Test Account:   testuser / password123"
echo "  Web Target:     http://${MY_IP}/login.php"
echo ""
echo "  Auth Logs:      /var/log/auth.log"
echo "  Apache Logs:    /var/log/apache2/access.log"
echo "════════════════════════════════════════════════════"
echo -e "${RED}  [!] This machine is intentionally vulnerable${NC}"
echo -e "${RED}  [!] Isolate from production networks${NC}${CYAN}"
echo "════════════════════════════════════════════════════"
echo -e "${NC}"
