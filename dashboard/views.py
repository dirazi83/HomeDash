from django.shortcuts import render
from django.core.cache import cache
from services.models import Service

def index_view(request):
    services = Service.objects.filter(is_active=True).order_by('name')
    return render(request, 'index.html', {'services': services, 'total_services': services.count()})

def widget_update(request, pk):
    """Returns the rendered widget template for a specific service."""
    try:
        service = Service.objects.get(pk=pk, is_active=True)
    except Service.DoesNotExist:
        return render(request, 'partials/widget_error.html', {'error': 'Service not found'})
        
    cache_key = f"service_stats_{service.pk}"
    stats = cache.get(cache_key)
    
    # Render a specific widget type based on service
    template_name = f'widgets/{service.service_type}.html'
    
    # Fallback to a generic widget if specific one doesn't exist
    from django.template.loader import get_template
    from django.template import TemplateDoesNotExist
    try:
        get_template(template_name)
    except TemplateDoesNotExist:
        template_name = 'widgets/generic.html'
        
    return render(request, template_name, {'service': service, 'stats': stats})

def settings_view(request):
    """View for dashboard settings."""
    from services.models import Service
    from django.core.cache import cache as _cache

    services = Service.objects.order_by('name')
    service_rows = []
    for svc in services:
        cached = _cache.get(f"service_stats_{svc.pk}") or {}
        service_rows.append({
            'service': svc,
            'is_cached': bool(cached),
            'version': cached.get('version'),
        })

    ctx = {
        'service_rows': service_rows,
        'total': services.count(),
        'online': services.filter(is_online=True).count(),
        'offline': services.filter(is_online=False).count(),
    }
    return render(request, 'settings.html', ctx)


def settings_trigger_poll(request):
    """Trigger an immediate Celery poll and return a status snippet."""
    if request.method != 'POST':
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(['POST'])
    try:
        from services.tasks import poll_service_stats
        poll_service_stats.delay()
        msg = 'Poll triggered — stats will refresh in a few seconds.'
        colour = 'text-emerald-500'
    except Exception as exc:
        msg = f'Error: {exc}'
        colour = 'text-destructive'
    from django.http import HttpResponse
    return HttpResponse(
        f'<span class="{colour} text-sm">{msg}</span>',
        content_type='text/html',
    )


def settings_clear_cache(request):
    """Clear all service_stats_* cache keys and return a status snippet."""
    if request.method != 'POST':
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(['POST'])
    try:
        from services.models import Service
        from django.core.cache import cache as _cache
        keys = [f"service_stats_{s.pk}" for s in Service.objects.all()]
        for k in keys:
            _cache.delete(k)
        msg = f'Cleared {len(keys)} cache entries.'
        colour = 'text-emerald-500'
    except Exception as exc:
        msg = f'Error: {exc}'
        colour = 'text-destructive'
    from django.http import HttpResponse
    return HttpResponse(
        f'<span class="{colour} text-sm">{msg}</span>',
        content_type='text/html',
    )


def qbittorrent_live(request, pk):
    """Live torrent table — fetched directly from qBittorrent WebUI."""
    from django.shortcuts import get_object_or_404
    from services.api import QBittorrentAPI

    service = get_object_or_404(Service, pk=pk, is_active=True)
    api = QBittorrentAPI(service)

    ctx = {'service': service, 'error': None,
           'torrents': [], 'dl_speed': 0, 'up_speed': 0, 'connection_status': 'disconnected'}
    try:
        live = api.fetch_live()
        if live['is_online']:
            ctx.update(live)
        else:
            ctx['error'] = 'Cannot connect to qBittorrent WebUI'
    except Exception as exc:
        ctx['error'] = str(exc)

    return render(request, 'partials/qbittorrent_live.html', ctx)


def jdownloader_live(request, pk):
    """Live download table for JDownloader — fetched directly, not from cache."""
    from django.shortcuts import get_object_or_404
    from services.api import JDownloaderAPI

    service = get_object_or_404(Service, pk=pk, is_active=True)

    ctx = {
        'service': service,
        'packages': [],
        'links': [],
        'state': 'UNKNOWN',
        'speed_bytes': 0,
        'total_bytes': 0,
        'loaded_bytes': 0,
        'link_count': 0,
        'running_downloads': 0,
        'error': None,
    }

    try:
        api = JDownloaderAPI(service)
        device = api._get_device()
        if device:
            ctx['state'] = device.downloadcontroller.get_current_state() or 'UNKNOWN'
            ctx['speed_bytes'] = device.downloadcontroller.get_speed_in_bytes() or 0

            packages = device.downloads.query_packages([{
                "bytesLoaded": True, "bytesTotal": True, "childCount": True,
                "enabled": True, "eta": True, "finished": True, "hosts": True,
                "running": True, "speed": True, "status": True,
                "maxResults": -1, "startAt": 0,
            }]) or []

            links = device.downloads.query_links([{
                "bytesLoaded": True, "bytesTotal": True, "enabled": True,
                "eta": True, "finished": True, "host": True, "running": True,
                "skipped": True, "speed": True, "status": True,
                "maxResults": -1, "startAt": 0,
            }]) or []

            for p in packages:
                eta = p.get('eta') or 0
                if eta > 3600:
                    p['display_eta'] = f"{eta // 3600}h {(eta % 3600) // 60}m"
                elif eta > 60:
                    p['display_eta'] = f"{eta // 60}m {eta % 60}s"
                elif eta > 0:
                    p['display_eta'] = f"{eta}s"
                else:
                    p['display_eta'] = ''

            ctx['packages'] = packages
            ctx['links'] = links
            ctx['link_count'] = len(links)
            ctx['running_downloads'] = sum(1 for lnk in links if lnk.get('running'))
            ctx['total_bytes'] = sum(p.get('bytesTotal') or 0 for p in packages)
            ctx['loaded_bytes'] = sum(p.get('bytesLoaded') or 0 for p in packages)
        else:
            ctx['error'] = 'Device not reachable'
    except Exception as exc:
        ctx['error'] = str(exc)

    return render(request, 'partials/jdownloader_live.html', ctx)

def proxmox_live(request, pk):
    """Live VM/container list for Proxmox — fetched directly, not from cache."""
    from django.shortcuts import get_object_or_404
    from services.api import ProxmoxAPI

    service = get_object_or_404(Service, pk=pk, is_active=True)
    api = ProxmoxAPI(service)
    ctx = {'service': service, 'vms': [], 'containers': [], 'error': None}
    try:
        live = api.fetch_live()
        if live['is_online']:
            ctx['vms'] = live['vms']
            ctx['containers'] = live['containers']
        else:
            ctx['error'] = 'Cannot connect to Proxmox'
    except Exception as exc:
        ctx['error'] = str(exc)
    return render(request, 'partials/proxmox_live.html', ctx)


def terminal_page(request):
    """Dedicated terminal page."""
    return render(request, 'terminal.html')


def notifications_view(request):
    """Returns dropdown content listing any offline services."""
    from services.models import Service
    from django.core.cache import cache as _cache

    services = Service.objects.filter(is_active=True).order_by('name')
    errors = []
    for svc in services:
        cached = _cache.get(f"service_stats_{svc.pk}")
        if cached is not None and not cached.get('is_online', True):
            errors.append({
                'name': svc.name,
                'pk': svc.pk,
                'type_display': svc.get_service_type_display(),
            })
    return render(request, 'partials/notifications_panel.html', {'errors': errors})


def notifications_dot(request):
    """Returns the notification dot element — replaces itself via HTMX every 30s."""
    from django.http import HttpResponse
    from services.models import Service
    from django.core.cache import cache as _cache

    services = Service.objects.filter(is_active=True)
    has_errors = any(
        not (_cache.get(f"service_stats_{s.pk}") or {}).get('is_online', True)
        for s in services
        if _cache.get(f"service_stats_{s.pk}") is not None
    )
    vis = '' if has_errors else 'hidden '
    return HttpResponse(
        f'<span id="notif-dot" hx-get="/notifications/dot/" hx-trigger="every 30s" hx-swap="outerHTML" '
        f'class="{vis}absolute top-1.5 right-1.5 block h-2 w-2 rounded-full bg-destructive ring-2 ring-background"></span>',
        content_type='text/html',
    )


def service_dashboard(request, pk):
    """View for a dedicated internal dashboard for a specific service."""
    from django.shortcuts import get_object_or_404
    service = get_object_or_404(Service, pk=pk, is_active=True)
    
    cache_key = f"service_stats_{service.pk}"
    stats = cache.get(cache_key)
    
    template_name = f'dashboards/{service.service_type}.html'
    from django.template.loader import get_template
    from django.template import TemplateDoesNotExist
    try:
        get_template(template_name)
    except TemplateDoesNotExist:
        template_name = 'dashboards/generic.html'
        
    return render(request, template_name, {'service': service, 'stats': stats})
