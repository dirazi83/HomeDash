from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
from .models import Service
from .api import RadarrAPI, SonarrAPI, TrueNASAPI, OverseerrAPI, ProwlarrAPI, JDownloaderAPI, QBittorrentAPI, PlexAPI, TautulliAPI, BazarrAPI, ProxmoxAPI, PfSenseAPI, HomeDashAPI, ServiceAPI

@shared_task
def poll_service_stats():
    """Polls all active services and caches their stats."""
    services = Service.objects.filter(is_active=True)

    for service in services:
        cache_key = f"service_stats_{service.pk}"

        # Determine API client based on service type
        api_map = {
            'radarr': RadarrAPI,
            'sonarr': SonarrAPI,
            'truenas': TrueNASAPI,
            'overseerr': OverseerrAPI,
            'prowlarr': ProwlarrAPI,
            'jdownloader': JDownloaderAPI,
            'qbittorrent': QBittorrentAPI,
            'plex': PlexAPI,
            'tautulli': TautulliAPI,
            'bazarr': BazarrAPI,
            'proxmox': ProxmoxAPI,
            'pfsense': PfSenseAPI,
            'homedash': HomeDashAPI,
        }

        api_class = api_map.get(service.service_type, ServiceAPI)
        api = api_class(service)

        # Fetch complete stats
        stats = api.fetch_stats()

        # Persist online status and last_checked to DB
        is_online = stats.get('is_online', False)
        if service.is_online != is_online:
            service.is_online = is_online
            service.last_checked = timezone.now()
            service.save(update_fields=['is_online', 'last_checked'])

        # Append UI rendering metadata
        stats.update({
            'last_checked': service.last_checked.isoformat() if service.last_checked else None,
            'type': service.service_type,
            'pk': service.pk,
            'name': service.name
        })

        # Cache stats for 60 seconds
        cache.set(cache_key, stats, timeout=60)

    return f"Polled {services.count()} services."
