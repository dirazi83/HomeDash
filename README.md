# HomeDash

A modern, self-hosted home server dashboard built with **Django 6**, **HTMX**, **Tailwind CSS**, **Celery**, and **Redis**. Monitor all your home server services from a single dark-themed interface.

![Python](https://img.shields.io/badge/Python-3.13-blue) ![Django](https://img.shields.io/badge/Django-6.0-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Features

| Feature | Description |
|---|---|
| **Service Widgets** | HTMX-powered cards that auto-refresh every 15s with live data |
| **Live Panels** | Real-time download/torrent/VM status with 8s polling (no cache) |
| **Web Terminal** | Full PTY shell via WebSocket (xterm.js + Django Channels) |
| **Error Notifications** | Bell icon polls every 30s, shows offline services as a dropdown |
| **First-run Wizard** | Auto-redirects on first launch to create the admin account |
| **User Login** | Session-based auth — all pages protected, login/logout flow |
| **Encrypted Secrets** | API keys and passwords are AES-encrypted at rest |
| **Background Polling** | Celery workers poll all services every 30s, cache TTL 60s |

---

## Supported Services

| Service | Widget | Dashboard | Live Panel |
|---|---|---|---|
| Radarr | ✅ | ✅ | — |
| Sonarr | ✅ | ✅ | — |
| TrueNAS | ✅ | ✅ | — |
| Overseerr | ✅ | ✅ | — |
| Prowlarr | ✅ | ✅ | — |
| Plex | ✅ | ✅ | — |
| Tautulli | ✅ | ✅ | — |
| Bazarr | ✅ | ✅ | — |
| qBittorrent | ✅ | ✅ | ✅ Real-time torrents |
| JDownloader | ✅ | ✅ | ✅ Real-time downloads |
| Proxmox | ✅ | ✅ | ✅ VM/LXC with CPU & RAM gauges |
| pfSense | ✅ | ✅ | — |

---

## Requirements

- Python 3.11+
- Redis (for cache + Celery broker)
- PostgreSQL (or SQLite for dev)
- Docker (optional, for Redis/Postgres)

---

## Quick Start

### 1. Clone & set up environment

```bash
git clone https://github.com/dirazi83/HomeDash.git
cd HomeDash

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your DB, Redis URL, and secret key
```

### 3. Start infrastructure

```bash
docker-compose up -d   # starts PostgreSQL + Redis
```

### 4. Run migrations

```bash
source venv/bin/activate
python manage.py migrate
```

### 5. Start services

**Terminal 1 — Celery worker:**
```bash
source venv/bin/activate
celery -A config worker -l info
```

**Terminal 2 — Web server (ASGI/Daphne, required for WebSocket terminal):**
```bash
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

> `daphne` is listed in `INSTALLED_APPS`, so `runserver` automatically uses the ASGI server with full WebSocket support.

### 6. First-run setup

Open `http://<your-server-ip>:8000` in a browser.

On first launch you will be redirected to the **setup wizard** at `/setup/` where you create your admin account. After that, all pages require login.

---

## Adding Services

1. Go to **Servers & Services** in the sidebar
2. Click **Add Service**
3. Select the service type, fill in the URL and credentials, then save
4. The widget appears on the dashboard immediately; Celery picks it up on the next poll cycle (≤30s)

---

## Service Configuration Guide

Each service requires different credentials. Find the right values below for each service type.

---

### Radarr

| Field | Value |
|---|---|
| **URL** | `http://192.168.1.x:7878` |
| **API Key** | Radarr → Settings → General → API Key |

---

### Sonarr

| Field | Value |
|---|---|
| **URL** | `http://192.168.1.x:8989` |
| **API Key** | Sonarr → Settings → General → API Key |

---

### Prowlarr

| Field | Value |
|---|---|
| **URL** | `http://192.168.1.x:9696` |
| **API Key** | Prowlarr → Settings → General → API Key |

---

### Overseerr

| Field | Value |
|---|---|
| **URL** | `http://192.168.1.x:5055` |
| **API Key** | Overseerr → Settings → General → API Key |

---

### Bazarr

| Field | Value |
|---|---|
| **URL** | `http://192.168.1.x:6767` |
| **API Key** | Bazarr → Settings → General → Security → API Key |

---

### Plex

| Field | Value |
|---|---|
| **URL** | `http://192.168.1.x:32400` |
| **API Key** | Your X-Plex-Token — find it via Settings → Troubleshooting → Get XML for any media item (look for `X-Plex-Token` in the URL) |

---

### Tautulli

| Field | Value |
|---|---|
| **URL** | `http://192.168.1.x:8181` |
| **API Key** | Tautulli → Settings → Web Interface → API Key |

---

### TrueNAS

| Field | Value |
|---|---|
| **URL** | `http://192.168.1.x` (or HTTPS) |
| **API Key** | TrueNAS → Credentials → API Keys → Add |

---

### qBittorrent

| Field | Value |
|---|---|
| **URL** | `http://192.168.1.x:8080` (WebUI URL) |
| **Username** | qBittorrent WebUI username (default: `admin`) |
| **Password** | qBittorrent WebUI password |

> API Key field is not used — leave it blank.

---

### JDownloader

| Field | Value |
|---|---|
| **URL** | `https://my.jdownloader.org` (prefilled — do not change) |
| **Username** | Your my.jdownloader.org account email |
| **Password** | Your my.jdownloader.org account password |
| **API Key** | Device name shown in the JDownloader app (leave blank to use the first available device) |

> Requires the `myjdapi` Python package: `pip install myjdapi pycryptodome`

---

### Proxmox

| Field | Value |
|---|---|
| **URL** | `https://192.168.1.x:8006` |
| **API Key** | Token ID in format `user@pam!tokenname` — create in Datacenter → Permissions → API Tokens |
| **Password** | API Token Secret (UUID shown once when the token is created) |

> Username field is not used when using an API token — leave it blank.

---

### pfSense

| Field | Value |
|---|---|
| **URL** | `https://192.168.1.1` (pfSense web UI URL) |
| **API Key** | `clientid clienttoken` — from System → API Keys (requires the [pfsense-api](https://github.com/jaredhendrickson13/pfsense-api) package). Leave blank to use username/password instead. |
| **Username** | `admin` (only needed if not using API Key) |
| **Password** | pfSense admin password (only needed if not using API Key) |

> pfSense uses a self-signed certificate by default — SSL verification is disabled automatically.
>
> **To install pfsense-api:** In pfSense go to System → Package Manager → Available Packages → search for `pfSense-pkg-API` and install it. Then configure API keys under System → API Keys.

---

## Project Structure

```
HomeDash/
├── config/           # Django settings, URLs, ASGI config
├── dashboard/        # Main app — views, widgets, live panels, terminal, auth
│   ├── consumers.py  # WebSocket PTY terminal consumer
│   ├── middleware.py # Setup redirect + login required middleware
│   └── routing.py    # WebSocket URL routing
├── services/         # Service models, API clients, Celery tasks
│   └── api.py        # API classes for all supported services
├── templates/
│   ├── base.html     # Sidebar layout, notifications bell
│   ├── login.html    # Login page
│   ├── setup.html    # First-run wizard
│   ├── terminal.html # xterm.js WebSocket terminal
│   ├── dashboards/   # Per-service dashboard pages
│   ├── widgets/      # Per-service widget cards
│   └── partials/     # HTMX live panel partials
└── requirements.txt
```

---

## Tech Stack

- **Backend:** Django 6.0, Django Channels 4, Daphne (ASGI)
- **Frontend:** HTMX 1.9, Tailwind CSS (CDN), xterm.js 5
- **Tasks:** Celery 5, Redis
- **Terminal:** WebSocket + Linux PTY (`pty` module)
- **Auth:** Django built-in sessions + custom setup/login middleware
