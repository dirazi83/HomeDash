# Home Server Dashboard

A modern, dark-themed admin dashboard for managing and monitoring home server services (like TrueNAS, Radarr, Sonarr) built with Django 5.2, HTMX, TailwindCSS, Celery, and Redis.

## Features
- **Dark UI**: Fully responsive Tailwind CSS dark mode design.
- **Dynamic Widgets**: HTMX-powered dashboard widgets that poll for real-time state without full page reloads.
- **Secure Integration**: API keys and passwords are symmetrically encrypted at rest (`cryptography`).
- **Asynchronous Monitoring**: Heavy API polling is offloaded to background Celery workers and cached into Redis for ultra-fast dashboard rendering.

---

## 🚀 Setup & Deployment Guide

This project requires **Python 3.11+**, **Docker**, and **Docker Compose** on your host server.

### 1. Environment Preparation
First, clone or navigate to the project directory on your server:
```bash
cd /root/HomeDashboard
```

### 2. Infrastructure (PostgreSQL & Redis)
The project relies on PostgreSQL for the primary database and Redis as a caching/message broker for Celery.
```bash
# Start the database and redis containers in the background
docker-compose up -d
```
*Note: This creates local named volumes (`postgres_data`) so your data persists.*

### 3. Python Virtual Environment
We strongly recommend running the Django application inside an isolated virtual environment.
```bash
# Create the virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install the Python dependencies
pip install -r requirements.txt
```

### 4. Database Setup & Migrations
Before starting the app, you need to configure the database schema and add the initial tables.
```bash
# Run Django Migrations (ensures your DB schema is current)
python manage.py migrate
```

### 5. Running the Application

To run the full stack, you need two processes running simultaneously. You can use something like `tmux`, `screen`, or set up `systemd` services to manage these in production.

**Terminal 1: Start the Celery Worker (Background Tasks)**
```bash
source venv/bin/activate
celery -A config worker -l info
```

**Terminal 2: Start the Django Web Server**
```bash
source venv/bin/activate
# Run the development server visible on your local network
python manage.py runserver 0.0.0.0:8000
```

### 6. Access the Dashboard
Open your web browser and navigate to the IP address of your server on port 8000:
👉 `http://192.168.15.251:8000`

---

## 🛠 Adding New Services
1. Navigate to the **"Servers & Services"** tab in the sidebar navigation.
2. Click **"Add Service"**.
3. Choose the Service Type (e.g., Radarr) and input its full API URL (e.g., `http://192.168.1.50:7878`). 
4. Paste the API Key. Once saved, the key is immediately encrypted.
5. The Celery worker will detect the new service automatically on its next cycle and populate the dashboard.
