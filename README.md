# HomeDash

A modern, self-hosted home server dashboard built with **Django 6**, **HTMX**, **Tailwind CSS**, **Celery**, and **Redis**. Monitor all your self-hosted services from a single beautiful dark-mode interface.

![HomeDash Dashboard](https://raw.githubusercontent.com/dirazi83/HomeDash/main/docs/screenshot.png)

## Features

- **12 Service Integrations** — Radarr, Sonarr, TrueNAS, Overseerr, Prowlarr, Plex, Tautulli, Bazarr, qBittorrent, JDownloader, Proxmox, pfSense
- **Live Panels** — Real-time torrent list, download queue, VM status, WAN traffic charts
- **pfSense Traffic Charts** — Live / 24h / 7d / 30d WAN bandwidth graphs
- **Web Terminal** — Browser-based SSH terminal powered by xterm.js + WebSockets
- **Background Polling** — Celery + Redis updates stats every 30 seconds
- **Backup & Restore** — One-click JSON export/import of all service configs
- **First-run Wizard** — Guided setup on first launch
- **Encrypted Credentials** — Service passwords stored encrypted in the database
- **User Authentication** — Login-protected dashboard

## Supported Services

| Service | Widget | Dashboard | Live Panel |
|---------|--------|-----------|------------|
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
| pfSense | ✅ | ✅ | ✅ Live WAN traffic chart |

## Quick Start (Docker — Recommended)

```bash
# 1. Pull the image
docker pull med10/homedash:latest

# 2. Download docker-compose.yml
curl -O https://raw.githubusercontent.com/dirazi83/HomeDash/main/docker-compose.yml

# 3. (Optional) customise credentials
cp .env.example .env && nano .env

# 4. Start everything
docker compose up -d

# 5. Open in browser
open http://localhost:3033
```

**Default login:** `admin` / `admin` (change after first login)

All services start automatically:
- **web** — Daphne ASGI server (HTTP + WebSockets)
- **celery** — Background polling worker
- **celery-beat** — Periodic task scheduler
- **db** — PostgreSQL 15
- **redis** — Redis 7

## Quick Start (Manual / Development)

### Requirements

- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### Setup

```bash
git clone https://github.com/dirazi83/HomeDash.git
cd HomeDash

python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Start infrastructure
docker compose up -d db redis

# Configure environment
cp .env.example .env   # edit DB_HOST=localhost, DB_PORT=5432

# Apply migrations and create admin user
python manage.py migrate
python manage.py createsuperuser

# Start all services (3 terminals)
daphne -b 0.0.0.0 -p 3033 config.asgi:application
celery -A config worker -l INFO
celery -A config beat -l INFO
```

Open http://localhost:3033

## Configuration

All settings can be passed as environment variables or in a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `django-insecure-...` | Django secret key — **change in production** |
| `DEBUG` | `False` | Enable Django debug mode |
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5433` | PostgreSQL port |
| `DB_NAME` | `homedash` | Database name |
| `DB_USER` | `admin` | Database user |
| `DB_PASSWORD` | `admin` | Database password |
| `REDIS_URL` | `redis://localhost:6379/1` | Redis URL (cache) |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker |
| `ADMIN_USER` | `admin` | Admin username created on first run |
| `ADMIN_PASSWORD` | `admin` | Admin password created on first run |
| `PORT` | `3033` | Web server port |

## Service Configuration Guide

Add services at **Settings → Add Service**. Use the fields below to configure each one.

### Radarr / Sonarr / Prowlarr
| Field | Value |
|-------|-------|
| URL | `http://host:7878` (Radarr) · `http://host:8989` (Sonarr) · `http://host:9696` (Prowlarr) |
| API Key | Settings → General → Security → API Key |

### TrueNAS
| Field | Value |
|-------|-------|
| URL | `http://host` or `https://host` |
| API Key | TrueNAS UI → Top-right menu → API Keys |

### Overseerr
| Field | Value |
|-------|-------|
| URL | `http://host:5055` |
| API Key | Settings → General → API Key |

### Plex
| Field | Value |
|-------|-------|
| URL | `http://host:32400` |
| API Key | X-Plex-Token (from Plex web → account → XML) |

### Tautulli
| Field | Value |
|-------|-------|
| URL | `http://host:8181` |
| API Key | Settings → Web Interface → API Key |

### Bazarr
| Field | Value |
|-------|-------|
| URL | `http://host:6767` |
| API Key | Settings → General → Security |

### qBittorrent
| Field | Value |
|-------|-------|
| URL | `http://host:8080` (WebUI URL) |
| Username | WebUI username |
| Password | WebUI password |

### JDownloader
| Field | Value |
|-------|-------|
| URL | `https://my.jdownloader.org` |
| Username | MyJDownloader email |
| Password | MyJDownloader password |
| API Key | Device name (from JDownloader → My.JDownloader settings) |

### Proxmox
| Field | Value |
|-------|-------|
| URL | `https://host:8006` |
| API Key | `USER@REALM!TOKENID=SECRET` (Datacenter → API Tokens) |

### pfSense
| Field | Value |
|-------|-------|
| URL | `https://host` |
| API Key | System → REST API → Create API Key (pfREST v2) |

> **Note:** Add `192.168.x.x` (your HomeDash server IP) to the pfSense Login Protection **Whitelist** to prevent automatic IP blocking.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 6.0 + Django Channels 4 |
| ASGI Server | Daphne 4.2 |
| Task Queue | Celery 5 + Redis |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| Frontend | HTMX 1.9 + Tailwind CSS (CDN) |
| Charts | Chart.js 4.4 |
| Terminal | xterm.js 5 + WebSockets + Linux PTY |
| Container | Docker + Docker Compose |

## Project Structure

```
HomeDash/
├── config/           # Django settings, URLs, ASGI/WSGI
├── dashboard/        # Main app: views, widgets, terminal
├── services/         # Service models, API clients, Celery tasks
├── templates/        # HTML templates
│   ├── dashboards/   # Per-service full dashboards
│   ├── widgets/      # Homepage widget cards
│   └── partials/     # HTMX partial templates
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
└── requirements.txt
```

## Docker Hub

```bash
docker pull med10/homedash:latest
```

[https://hub.docker.com/r/med10/homedash](https://hub.docker.com/r/med10/homedash)

## License

MIT
