# Quick Start Guide - HomeDashboard API Integrations

This guide gets you up and running with the enhanced HomeDashboard in **5 minutes**.

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- A running Radarr/Sonarr/TrueNAS instance
- API keys from your services

## Step 1: Start Infrastructure (2 minutes)

```bash
cd /root/HomeDashboard

# Start PostgreSQL and Redis
docker-compose up -d

# Activate virtual environment
source venv/bin/activate

# Run migrations
python manage.py migrate
```

## Step 2: Start Services (1 minute)

Open two terminal windows:

**Terminal 1 - Celery Worker**:
```bash
source venv/bin/activate
celery -A config worker -l info
```

**Terminal 2 - Django Server**:
```bash
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

## Step 3: Add Your First Service (2 minutes)

1. Open browser: `http://localhost:8000` (or `http://your-server-ip:8000`)
2. Click **"Servers & Services"** in sidebar
3. Click **"Add Service"**
4. Fill in the form:

### For Radarr:
- **Name**: My Radarr
- **Service Type**: Radarr
- **URL**: `http://192.168.1.50:7878` (your Radarr IP and port)
- **API Key**: Get from Radarr → Settings → General → Security → API Key

### For Sonarr:
- **Name**: My Sonarr
- **Service Type**: Sonarr
- **URL**: `http://192.168.1.50:8989`
- **API Key**: Get from Sonarr → Settings → General → Security → API Key

### For TrueNAS:
- **Name**: My TrueNAS
- **Service Type**: TrueNAS
- **URL**: `http://192.168.1.100` (or `https://...`)
- **API Key**: Get from TrueNAS → Settings → API Keys → Add

5. Click **Save**

## Step 4: View Your Dashboard

1. Return to main dashboard (`/`)
2. Wait ~10 seconds for background sync
3. See your service widget with live stats!
4. Click on the widget to open full dashboard

## What You Get

### Radarr Dashboard
- ✅ Total movies: `{{ count }}`
- ✅ Downloaded: `{{ count }}`
- ✅ Missing: `{{ count }}`
- ✅ Queue: `{{ count }} downloading`
- ✅ Full management interface with 5 tabs

### Sonarr Dashboard
- ✅ Total series: `{{ count }}`
- ✅ Episodes: `{{ downloaded }}/{{ total }}`
- ✅ Missing episodes: `{{ count }}`
- ✅ Queue: `{{ count }} downloading`
- ✅ Upcoming episodes (next 7 days)

### TrueNAS Dashboard
- ✅ Storage pools: `{{ count }}`
- ✅ Pool health status
- ✅ Storage usage with visual bars
- ✅ System alerts
- ✅ Uptime and version

## Quick Actions

### Search and Add a Movie (Radarr)
1. Click Radarr widget
2. Click "Add Movie" button
3. Search for movie name
4. Select movie and configure
5. Click Add

### Monitor Downloads
1. Click any *arr service widget
2. Go to "Queue" tab
3. See real-time progress bars
4. Remove items if needed

### Check Storage (TrueNAS)
1. Click TrueNAS widget
2. View all pools with health status
3. Check alerts (if any)
4. Monitor usage percentages

## Customization

### Change Widget Refresh Rate

Edit `templates/widgets/{service}.html`:
```html
<!-- Change from 10s to 30s -->
hx-trigger="every 30s"
```

### Customize Stats Display

Edit `dashboard/dashboard_config.py`:
```python
from dashboard.dashboard_config import RADARR_CONFIG

# Hide missing movies count
RADARR_CONFIG.widget.show_missing_count = False

# Change refresh interval
RADARR_CONFIG.widget.refresh_interval = 30
```

## Troubleshooting

### Widget shows "Awaiting background sync"
**Solution**: Wait 60 seconds for Celery to poll services

### "Service unreachable"
**Solutions**:
1. Check service is running
2. Verify URL is correct (including port)
3. Test API key in service UI
4. Check firewall allows connections

### Stats not updating
**Solutions**:
1. Check Celery worker is running
2. Check Redis is running: `docker ps`
3. Restart Celery worker

### Celery not starting
**Solution**:
```bash
# Check Redis connection
docker ps | grep redis

# Restart Redis if needed
docker-compose restart redis

# Clear Celery cache
celery -A config purge
```

## API Usage Examples

### Python Shell

```bash
python manage.py shell
```

```python
from services.models import Service
from services.api import RadarrAPI, SonarrAPI, TrueNASAPI

# Get your service
radarr = Service.objects.get(service_type='radarr')
api = RadarrAPI(radarr)

# Test connection
if api.test_connection():
    print("Connected!")

# Get stats
stats = api.fetch_stats()
print(f"Movies: {stats['total_movies']}")
print(f"Downloaded: {stats['downloaded_movies']}")

# Search for a movie
results = api.search_movies("The Matrix")
print(results[0]['title'])

# Get queue
queue = api.get_queue()
print(f"Queue size: {queue['totalRecords']}")
```

## Next Steps

1. **Explore Dashboards**: Click on service widgets to see full interfaces
2. **Read Documentation**: Check [ALL_SERVICES_API_GUIDE.md](ALL_SERVICES_API_GUIDE.md)
3. **Add More Services**: Repeat Step 3 for other services
4. **Customize**: Adjust colors, refresh rates, stats display
5. **Monitor**: Use the dashboard daily for your home server

## Documentation Index

- **Quick Start**: This file
- **Complete Guide**: [ALL_SERVICES_API_GUIDE.md](ALL_SERVICES_API_GUIDE.md)
- **Radarr Specific**: [RADARR_API_GUIDE.md](RADARR_API_GUIDE.md)
- **Implementation Details**: [COMPLETE_IMPLEMENTATION_SUMMARY.md](COMPLETE_IMPLEMENTATION_SUMMARY.md)
- **Testing Checklist**: [RADARR_IMPLEMENTATION_CHECKLIST.md](RADARR_IMPLEMENTATION_CHECKLIST.md)

## Service-Specific Setup

### Radarr Setup
```
Settings → General → Security
Copy API Key
Add to HomeDashboard with:
- URL: http://ip:7878
- API Key: (paste)
```

### Sonarr Setup
```
Settings → General → Security
Copy API Key
Add to HomeDashboard with:
- URL: http://ip:8989
- API Key: (paste)
```

### TrueNAS Setup
```
System → API Keys → Add
Copy API Key
Add to HomeDashboard with:
- URL: http://ip (or https://)
- API Key: (paste)
```

## Performance Tips

1. **Cache is King**: Stats cached for 60 seconds
2. **Background Workers**: Celery handles heavy lifting
3. **HTMX Magic**: Only updates changed parts of page
4. **Pagination**: Large datasets load in chunks

## Security Notes

- ✅ API keys encrypted at rest
- ✅ HTTPS supported
- ✅ No keys in logs
- ✅ Request timeouts
- ✅ CSRF protection

## Common Commands

```bash
# Start everything
docker-compose up -d && source venv/bin/activate

# Run migrations
python manage.py migrate

# Start Celery worker
celery -A config worker -l info

# Start Django
python manage.py runserver 0.0.0.0:8000

# Check service status
python manage.py shell
>>> from services.models import Service
>>> Service.objects.all()

# Clear cache
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()

# View logs
docker-compose logs redis
docker-compose logs postgres
```

## Success Checklist

After following this guide, you should have:

- [ ] Docker containers running (Redis, PostgreSQL)
- [ ] Celery worker running
- [ ] Django server running
- [ ] At least one service added
- [ ] Widget showing live stats
- [ ] Full dashboard accessible
- [ ] Stats updating automatically

## Get Help

If you encounter issues:

1. Check this guide's troubleshooting section
2. Review [ALL_SERVICES_API_GUIDE.md](ALL_SERVICES_API_GUIDE.md)
3. Check application logs
4. Verify service API endpoints
5. Test API keys in service UI

## What's Next?

Now that you're set up:

1. **Add all your services**: Radarr, Sonarr, TrueNAS, etc.
2. **Customize dashboards**: Adjust colors, stats, refresh rates
3. **Explore features**: Use the full management capabilities
4. **Monitor regularly**: Check stats, queue, health
5. **Automate**: Let Celery handle background polling

---

**Congratulations! Your HomeDashboard is now a powerful management hub for your home server! 🎉**

For advanced usage, see [ALL_SERVICES_API_GUIDE.md](ALL_SERVICES_API_GUIDE.md)
