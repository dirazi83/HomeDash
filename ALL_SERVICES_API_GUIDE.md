# Complete API Integration Guide - All Services

This guide provides comprehensive documentation for ALL service integrations in the HomeDashboard application.

## Table of Contents

1. [Radarr (Movies)](#radarr-movies)
2. [Sonarr (TV Series)](#sonarr-tv-series)
3. [TrueNAS (Storage)](#truenas-storage)
4. [Quick Reference](#quick-reference)

---

## Radarr (Movies)

### Overview
Comprehensive Radarr v3 API integration for managing your movie library.

### Features
- **Movie Management**: Add, edit, delete, search movies
- **Queue Monitoring**: Real-time download queue
- **Calendar**: Upcoming movie releases
- **History**: Download activity
- **Quality Profiles**: Manage quality settings
- **System Info**: Status, disk space, health

### Quick Start
```python
from services.api import RadarrAPI
from services.models import Service

service = Service.objects.get(service_type='radarr')
api = RadarrAPI(service)

# Search and add a movie
results = api.search_movies("Inception")
movie_data = results[0]
movie_data.update({
    'qualityProfileId': 1,
    'rootFolderPath': '/movies',
    'monitored': True
})
api.add_movie(movie_data)
```

### Stats Available
- Total movies
- Downloaded movies
- Monitored movies
- Missing movies
- Queue size
- Disk space
- Upcoming movies

### Dashboard Features
- 5-tab interface (Movies, Queue, Calendar, History, System)
- Real-time updates via HTMX
- Movie search and management
- Queue monitoring with progress bars
- Calendar of upcoming releases

**Detailed Documentation**: See [RADARR_API_GUIDE.md](RADARR_API_GUIDE.md)

---

## Sonarr (TV Series)

### Overview
Comprehensive Sonarr v3 API integration for managing TV series and episodes.

### Features
- **Series Management**: Add, edit, delete, search series
- **Episode Tracking**: Monitor individual episodes
- **Queue Monitoring**: Real-time download queue
- **Calendar**: Upcoming episode air dates
- **History**: Download activity
- **Quality Profiles**: Manage quality settings
- **System Info**: Status, disk space, health

### Quick Start
```python
from services.api import SonarrAPI
from services.models import Service

service = Service.objects.get(service_type='sonarr')
api = SonarrAPI(service)

# Search and add a series
results = api.search_series("Breaking Bad")
series_data = results[0]
series_data.update({
    'qualityProfileId': 1,
    'rootFolderPath': '/tv',
    'monitored': True,
    'seasonFolder': True
})
api.add_series(series_data)

# Get episodes for a series
episodes = api.get_episodes(series_id=1)
```

### API Methods

#### Series Management
```python
# Get all series
series = api.get_series()

# Get specific series
series = api.get_series_by_id(1)

# Search for series
results = api.search_series("Game of Thrones")

# Add series
api.add_series(series_data)

# Update series
api.update_series(series_id=1, series_data=updated_data)

# Delete series
api.delete_series(series_id=1, delete_files=True)
```

#### Episode Management
```python
# Get all episodes for a series
episodes = api.get_episodes(series_id=1)

# Get specific season
episodes = api.get_episodes(series_id=1, season_number=2)
```

#### Queue & Downloads
```python
# Get download queue
queue = api.get_queue(page=1, page_size=20)

# Delete from queue
api.delete_queue_item(queue_id=123, blocklist=True)
```

#### Calendar & History
```python
# Get upcoming episodes (next 7 days)
from datetime import datetime, timedelta
start = datetime.now().strftime('%Y-%m-%d')
end = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
calendar = api.get_calendar(start_date=start, end_date=end)

# Get history
history = api.get_history(page=1, page_size=20)

# Get missing episodes
missing = api.get_missing_episodes(page=1, page_size=20)
```

#### System
```python
# System status
status = api.get_system_status()

# Disk space
space = api.get_disk_space()

# Quality profiles
profiles = api.get_quality_profiles()

# Root folders
folders = api.get_root_folders()
```

### Stats Available
- Total series
- Total episodes
- Monitored series
- Downloaded episodes
- Missing episodes
- Queue size
- Disk space
- Upcoming episodes (next 7 days)

### Dashboard Features
- Status overview with 5 stats cards
- Upcoming episodes list with air dates
- Series/episode counts
- Queue monitoring
- Disk space visualization
- System information

### Widget Display
- Total series count
- Downloaded episodes
- Missing episodes count
- Queue size
- Version
- Online/offline status

---

## TrueNAS (Storage)

### Overview
Comprehensive TrueNAS API v2.0 integration for managing network-attached storage.

### Features
- **Storage Pools**: Monitor ZFS pools and health
- **Datasets**: View and manage datasets
- **Shares**: SMB/NFS share management
- **Services**: Start/stop system services
- **Alerts**: System health alerts
- **System Info**: Version, uptime, hostname

### Quick Start
```python
from services.api import TrueNASAPI
from services.models import Service

service = Service.objects.get(service_type='truenas')
api = TrueNASAPI(service)

# Get storage pools
pools = api.get_pools()
for pool in pools:
    print(f"{pool['name']}: {pool['status']} - {pool['healthy']}")

# Get system alerts
alerts = api.get_alerts()
for alert in alerts:
    print(f"[{alert['level']}] {alert['formatted']}")
```

### API Methods

#### Storage Management
```python
# Get all pools
pools = api.get_pools()

# Get specific pool
pool = api.get_pool(pool_id=1)

# Get datasets
datasets = api.get_datasets()
datasets = api.get_datasets(pool_name='tank')

# Create dataset
api.create_dataset(name='media', pool='tank', compression='lz4')

# Delete dataset
api.delete_dataset('tank/media')
```

#### Sharing
```python
# SMB Shares
smb_shares = api.get_smb_shares()
api.create_smb_share(path='/mnt/tank/share', name='MyShare', comment='Shared folder')

# NFS Shares
nfs_shares = api.get_nfs_shares()
```

#### Services
```python
# Get all services
services = api.get_services()

# Start service
api.start_service('cifs')

# Stop service
api.stop_service('cifs')
```

#### System
```python
# System information
info = api.get_system_info()
print(f"Hostname: {info['hostname']}")
print(f"Version: {info['version']}")
print(f"Uptime: {info['uptime_seconds']} seconds")

# Get alerts
alerts = api.get_alerts()

# Reboot (use with caution!)
# api.reboot()

# Shutdown (use with caution!)
# api.shutdown()
```

### Stats Available
- Hostname
- Version
- Uptime
- CPU usage
- Memory usage
- Storage pools (count, status, usage)
- System alerts
- Datasets count

### Dashboard Features
- Pool status with health indicators
- Storage usage visualization with progress bars
- Critical/warning/info alerts display
- System information (version, hostname, uptime)
- Pool capacity warnings (>90% = red, >75% = yellow)

### Widget Display
- Hostname
- Pool count
- Alert count (color-coded)
- Version
- Online/offline status

---

## Quick Reference

### Service Type Mapping

| Service | Type String | API Class | Port (Default) |
|---------|-------------|-----------|----------------|
| Radarr | `radarr` | `RadarrAPI` | 7878 |
| Sonarr | `sonarr` | `SonarrAPI` | 8989 |
| TrueNAS | `truenas` | `TrueNASAPI` | 80/443 |
| Overseerr | `overseerr` | `ServiceAPI` | 5055 |
| Prowlarr | `prowlarr` | `ServiceAPI` | 9696 |
| Plex | `plex` | `ServiceAPI` | 32400 |
| qBittorrent | `qbittorrent` | `ServiceAPI` | 8080 |
| Tautulli | `tautulli` | `ServiceAPI` | 8181 |
| JDownloader | `jdownloader` | `ServiceAPI` | Varies |
| Other | `other` | `ServiceAPI` | Varies |

### Authentication Methods

| Service | Method | Header/Param |
|---------|--------|--------------|
| Radarr | API Key | `X-Api-Key` header |
| Sonarr | API Key | `X-Api-Key` header |
| TrueNAS | API Key | `Authorization: Bearer {key}` |
| Overseerr | API Key | `X-Api-Key` header |
| Prowlarr | API Key | `X-Api-Key` header |

### Common Operations

#### Adding a Service
```python
from services.models import Service

service = Service.objects.create(
    name='My Radarr',
    service_type='radarr',
    url='http://192.168.1.50:7878',
    is_active=True
)
service.api_key = 'your-api-key-here'  # Will be encrypted
service.save()
```

#### Testing Connection
```python
from services.api import RadarrAPI

api = RadarrAPI(service)
if api.test_connection():
    print("Connected successfully!")
else:
    print("Connection failed")
```

#### Getting Stats
```python
stats = api.fetch_stats()
print(f"Online: {stats['is_online']}")
print(f"Version: {stats['version']}")
```

### Dashboard Templates

Each service type has dedicated templates:

**Widgets** (`templates/widgets/`):
- `radarr.html` - Green theme, movie stats
- `sonarr.html` - Blue theme, series/episode stats
- `truenas.html` - Cyan theme, storage stats
- `generic.html` - Fallback for other services

**Dashboards** (`templates/dashboards/`):
- `radarr.html` - Full movie management interface
- `sonarr.html` - Full series management interface
- `truenas.html` - Storage pool and alert management
- `generic.html` - Basic info for other services

### Configuration

#### Widget Refresh Intervals
Default: 10 seconds for all widgets

Customize in templates:
```html
hx-trigger="every 30s"  <!-- Change to 30 seconds -->
```

#### Cache Timeouts
Defined in `services/tasks.py`:
- Stats cache: 60 seconds
- Service polling: Every minute (Celery beat)

### Color Schemes

Each service has a distinct color theme:

- **Radarr**: Emerald/Green (#10b981)
- **Sonarr**: Blue (#3b82f6)
- **TrueNAS**: Cyan (#06b6d4)
- **Generic**: Muted gray

### File Structure

```
services/
├── api.py                          # All API client classes
├── tasks.py                        # Celery background tasks
├── models.py                       # Service model
├── views.py                        # Service management views
├── radarr_views.py                 # Radarr-specific views
└── templates/
    └── services/
        └── radarr/partials/        # Radarr HTMX partials

templates/
├── widgets/
│   ├── radarr.html                 # Radarr widget
│   ├── sonarr.html                 # Sonarr widget
│   ├── truenas.html                # TrueNAS widget
│   └── generic.html                # Generic widget
└── dashboards/
    ├── radarr.html                 # Radarr dashboard
    ├── sonarr.html                 # Sonarr dashboard
    ├── truenas.html                # TrueNAS dashboard
    └── generic.html                # Generic dashboard
```

### Error Handling

All API methods include error handling:

```python
# Methods return None on error
result = api.get_movies()
if result is None:
    print("API call failed")

# Boolean methods return False on error
success = api.delete_movie(999)
if not success:
    print("Delete operation failed")
```

### Performance Tips

1. **Use Caching**: Stats are cached for 60 seconds
2. **Pagination**: Use pagination for large datasets
3. **Background Tasks**: Heavy operations run in Celery
4. **Timeouts**: All requests have 10-second timeouts

### Security

- API keys encrypted at rest (Fernet encryption)
- Keys only decrypted when making requests
- HTTPS supported for all services
- No API keys in logs or error messages
- Request timeouts prevent hanging

### Troubleshooting

**Service shows "Awaiting background sync"**
- Wait 60 seconds for Celery worker
- Check Celery worker is running: `celery -A config worker -l info`

**"Service unreachable"**
- Verify service is running
- Check URL and port are correct
- Test API key in service UI
- Check firewall settings

**Stats not updating**
- Check Celery worker logs
- Verify Redis is running
- Check service API is responding

**Template not found**
- Ensure template exists in correct location
- Check service_type matches template name
- Falls back to `generic.html` if specific template missing

### Future Enhancements

Planned features for all services:
- Bulk operations
- Advanced filtering and search
- Custom dashboards per service
- Real-time WebSocket updates
- Mobile app support
- Notification management
- Automated maintenance tasks

### API Endpoint Coverage

**Radarr**: 35+ endpoints implemented
**Sonarr**: 30+ endpoints implemented
**TrueNAS**: 20+ endpoints implemented

See individual service guides for complete endpoint lists.

### Contributing

To add a new service integration:

1. Create API class in `services/api.py`
2. Implement `_request()`, `test_connection()`, `fetch_stats()`
3. Add service type to `services/tasks.py` api_map
4. Create widget template in `templates/widgets/{service}.html`
5. Create dashboard template in `templates/dashboards/{service}.html`
6. Update documentation

### Support

For issues or questions:
- Review service-specific documentation
- Check application logs
- Verify service API is accessible
- Test API key in service UI

### License

Same as HomeDashboard main project.

---

## Summary

This HomeDashboard now provides **comprehensive API integration** for:

✅ **Radarr** - Complete movie management (50+ methods)
✅ **Sonarr** - Complete TV series management (30+ methods)
✅ **TrueNAS** - Storage and NAS management (20+ methods)

All with:
- Enhanced statistics
- Custom dashboards
- Real-time updates
- Beautiful UI
- Comprehensive documentation

**Total API Methods**: 100+ across all services
**Total Endpoints**: 85+ API endpoints covered
**Template Files**: 15+ custom templates
