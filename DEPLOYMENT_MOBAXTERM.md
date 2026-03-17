# PisoFi Commander Deployment Guide (MobaXterm)

This guide shows how to install and run PisoFi Commander from **Windows using MobaXterm** to connect to your Linux box (Orange Pi / Raspberry Pi / x86).

---

## 1) What you need

- A Linux machine (Ubuntu/Debian recommended)
  - Orange Pi / Raspberry Pi / x86/x64
- Network access to that machine via SSH
- MobaXterm installed on Windows
- `git` access to your project files

---

## 2) Connect with MobaXterm

1. Open **MobaXterm**
2. Click **Session** → **SSH**
3. Enter:
   - **Remote host**: your board/server IP (example: `192.168.1.50`)
   - **Username**: your Linux user (example: `pi`, `orangepi`, `root`)
4. Click **OK** and login with password/key

After login, you will see a Linux terminal in MobaXterm.

---

## 3) Install system dependencies

Run these commands in the SSH terminal:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nodejs npm yarn nginx git
```

> If `yarn` is missing after install:

```bash
sudo npm install -g yarn
```

---

## 4) Copy or clone the project

### Option A: Clone from git
```bash
cd /opt
sudo git clone <YOUR_REPO_URL> pisofi-commander
sudo chown -R $USER:$USER /opt/pisofi-commander
cd /opt/pisofi-commander
```

### Option B: Drag-and-drop upload from MobaXterm
- Use the left SFTP panel in MobaXterm and upload your app folder to `/opt/pisofi-commander`.

---

## 5) Backend setup (FastAPI + SQLite)

```bash
cd /opt/pisofi-commander/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create backend env file:

```bash
cp .env .env.prod
```

Edit `.env.prod` and ensure:

```env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="test_database"
CORS_ORIGINS="*"
```

> Notes:
> - The app now uses SQLite (`backend/pisofi.db`) for PisoFi data.
> - Keep `MONGO_URL` present to match existing app expectations.

---

## 6) Frontend setup (React)

```bash
cd /opt/pisofi-commander/frontend
yarn install
```

Create frontend env:

```bash
cp .env .env.prod
```

Edit `frontend/.env.prod`:

```env
REACT_APP_BACKEND_URL=http://<SERVER_IP_OR_DOMAIN>
WDS_SOCKET_PORT=443
ENABLE_HEALTH_CHECK=false
```

Build frontend:

```bash
yarn build
```

This creates static files in `frontend/build`.

---

## 7) Create systemd service for backend

Create file:

```bash
sudo nano /etc/systemd/system/pisofi-backend.service
```

Paste:

```ini
[Unit]
Description=PisoFi Commander FastAPI Backend
After=network.target

[Service]
User=%i
WorkingDirectory=/opt/pisofi-commander/backend
EnvironmentFile=/opt/pisofi-commander/backend/.env.prod
ExecStart=/opt/pisofi-commander/backend/.venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable pisofi-backend.service
sudo systemctl start pisofi-backend.service
sudo systemctl status pisofi-backend.service
```

---

## 8) Configure Nginx (frontend + API reverse proxy)

Create Nginx site:

```bash
sudo nano /etc/nginx/sites-available/pisofi
```

Paste:

```nginx
server {
    listen 80;
    server_name _;

    root /opt/pisofi-commander/frontend/build;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8001/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location / {
        try_files $uri /index.html;
    }
}
```

Enable site and restart Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/pisofi /etc/nginx/sites-enabled/pisofi
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

Open in browser:

```text
http://<SERVER_IP>
```

---

## 9) GPIO notes for hardware

- **Raspberry Pi / Orange Pi**: GPIO mode can be enabled from Hardware Profile page.
- **x86/x64**: GPIO is intentionally disabled by design.
- Set board profile and pin mapping in the app:
  - Raspberry Pi: `coin=2`, `relay=3`, `bill=4`
  - Orange Pi Zero 3: `coin=229`, `relay=228`, `bill=72`

---

## 10) VLAN config deployment

1. In app, go to **Config Export**
2. Copy generated script
3. Save on server:

```bash
nano /opt/pisofi-vlan-apply.sh
chmod +x /opt/pisofi-vlan-apply.sh
sudo /opt/pisofi-vlan-apply.sh
```

> Adjust interface names (`eth0`, etc.) to your device.

---

## 11) Useful maintenance commands

```bash
# backend logs
sudo journalctl -u pisofi-backend.service -f

# restart backend
sudo systemctl restart pisofi-backend.service

# restart nginx
sudo systemctl restart nginx
```

---

## 12) Quick validation checklist

- [ ] Dashboard loads
- [ ] Can create sub-vendo VLAN
- [ ] Can generate and redeem PIN voucher
- [ ] GPIO actions work on OPI/RPI profiles
- [ ] x86 profile blocks GPIO actions
- [ ] Config export produces VLAN script

---

If you want, next I can also generate a **single one-command installer script** (`install.sh`) for this same MobaXterm flow.
