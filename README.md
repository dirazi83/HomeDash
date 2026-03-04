# HomeDash

A modern, self-hosted home server dashboard built with **Django 6**, **HTMX**, **Tailwind CSS**, **Celery**, and **Redis**. Monitor all your home server services from a single dark-themed interface.

![Python](https://img.shields.io/badge/Python-3.13-blue) ![Django](https://img.shields.io/badge/Django-6.0-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Features

| Feature | Description |
|---|---|
| **Service Widgets** | HTMX-powered cards that auto-refresh every 10s from Redis cache |
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
3. Select the service type and fill in the URL, API key, and credentials
4. The Celery worker picks it up on the next poll cycle (≤30s)

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
