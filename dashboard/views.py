import time as _time
from django.shortcuts import render
from django.http import JsonResponse
from django.core.cache import cache
from services.models import Service
from services.api import (RadarrAPI, SonarrAPI, TrueNASAPI, OverseerrAPI, ProwlarrAPI,
                          JDownloaderAPI, QBittorrentAPI, PlexAPI, TautulliAPI, BazarrAPI,
                          ProxmoxAPI, PfSenseAPI, HomeDashAPI, ServiceAPI)

_API_MAP = {
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

def _fetch_live_stats(service):
    """Fetch stats directly from the service API, bypassing Redis cache.

    This is used by the background polling task.  Calling it from a web view can
    block user requests for several seconds if the remote service is slow or
    unreachable, so higher‑level helpers should prefer the cache instead.
    """
    api_class = _API_MAP.get(service.service_type, ServiceAPI)
    return api_class(service).fetch_stats()


def _get_stats(service, force_live: bool = False) -> dict:
    """Return stats for *service*.

    If `force_live` is False the function first attempts to read a cached value
    (see :mod:`services.tasks.poll_service_stats`).  If the cache is empty or
    `force_live` is True it falls back to calling :func:`_fetch_live_stats` and
    then stores the result in the cache for 60 seconds.
    """
    from django.core.cache import cache as _cache

    cache_key = f"service_stats_{service.pk}"
    if not force_live:
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

    stats = _fetch_live_stats(service)
    _cache.set(cache_key, stats, timeout=60)
    return stats

def index_view(request):
    services = Service.objects.filter(is_active=True).order_by('name')
    return render(request, 'index.html', {'services': services, 'total_services': services.count()})

def widget_update(request, pk):
    """Return the rendered widget template for a specific service.

    This view is hit via HTMX polling on the index page; by default it reads
    from the cache so that dashboard rendering remains snappy.  The cache is
    populated every minute by ``services.tasks.poll_service_stats``.  If the
    service record vanishes we return an empty response so HTMX removes the
    enclosing element.
    """
    try:
        service = Service.objects.get(pk=pk, is_active=True)
    except Service.DoesNotExist:
        from django.http import HttpResponse
        return HttpResponse('')

    stats = _get_stats(service)

    template_name = f'widgets/{service.service_type}.html'
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


def settings_backup(request):
    """Create a JSON backup of all service configs and return it as a download."""
    import subprocess, datetime, os
    from django.http import HttpResponse, HttpResponseNotAllowed
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    try:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, f'homedash_backup_{timestamp}.json')

        result = subprocess.run(
            ['python', 'manage.py', 'dumpdata',
             '--natural-foreign', '--natural-primary',
             '--exclude=contenttypes', '--exclude=auth.permission',
             '-o', backup_path],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or 'dumpdata failed')

        with open(backup_path, 'rb') as f:
            data = f.read()

        response = HttpResponse(data, content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="homedash_backup_{timestamp}.json"'
        return response
    except Exception as exc:
        return HttpResponse(
            f'<span class="text-destructive text-sm">Backup failed: {exc}</span>',
            content_type='text/html',
        )


def settings_restore(request):
    """Restore service configs from an uploaded JSON backup file."""
    import json as _json_mod, os
    from django.http import HttpResponse, HttpResponseNotAllowed
    from django.core.management import call_command
    from io import StringIO
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    try:
        uploaded = request.FILES.get('backup_file')
        if not uploaded:
            raise ValueError('No file uploaded.')
        if not uploaded.name.endswith('.json'):
            raise ValueError('File must be a .json backup.')

        raw = uploaded.read().decode('utf-8')
        # Validate it's valid JSON
        _json_mod.loads(raw)

        # Save to temp file then loaddata
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp.write(raw)
            tmp_path = tmp.name

        out = StringIO()
        call_command('loaddata', tmp_path, stdout=out, stderr=out)
        os.unlink(tmp_path)

        from django.http import HttpResponseRedirect
        return HttpResponseRedirect('/settings/?restored=1')
    except Exception as exc:
        return HttpResponse(
            f'<span class="text-destructive text-sm">Restore failed: {exc}</span>',
            content_type='text/html',
        )


def settings_check_update(request):
    """Check Docker Hub for a newer image and return an HTMX snippet."""
    import urllib.request, json, os
    from django.http import HttpResponse
    from datetime import datetime

    build_date_str = os.environ.get('BUILD_DATE', '')

    update_btn = (
        '<button hx-post="/settings/apply-update/" hx-target="#update-result" hx-swap="innerHTML" '
        'hx-confirm="This will pull the latest image and restart all containers. Continue?" '
        'class="mt-2 inline-flex items-center gap-2 rounded-md bg-amber-500 hover:bg-amber-600 '
        'text-white h-8 px-3 text-xs font-medium transition-colors">'
        'Update Now</button>'
    )

    try:
        url = 'https://hub.docker.com/v2/repositories/med10/homedash/tags/latest'
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
        last_pushed = data.get('tag_last_pushed', '')
        if not last_pushed:
            raise ValueError('No push date from Docker Hub')

        pushed_dt = datetime.fromisoformat(last_pushed.replace('Z', '+00:00'))
        pushed_str = pushed_dt.strftime('%Y-%m-%d %H:%M UTC')

        if build_date_str and build_date_str != 'unknown':
            build_dt = datetime.fromisoformat(build_date_str.replace('Z', '+00:00'))
            if pushed_dt > build_dt:
                html = (
                    f'<span class="text-amber-400 text-xs font-medium">'
                    f'Update available — pushed {pushed_str}.</span>{update_btn}'
                )
            else:
                html = '<span class="text-emerald-500 text-xs font-medium">You are up to date.</span>'
        else:
            html = f'<span class="text-xs text-muted-foreground">Latest image pushed {pushed_str}.</span>{update_btn}'
    except Exception:
        html = '<span class="text-xs text-destructive">Could not reach Docker Hub.</span>'

    return HttpResponse(html, content_type='text/html')


def settings_apply_update(request):
    """Trigger a Watchtower HTTP API update for labelled containers."""
    import urllib.request, os
    from django.http import HttpResponse, HttpResponseNotAllowed

    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    token = os.environ.get('WATCHTOWER_TOKEN', 'homedash-update-token')
    try:
        req = urllib.request.Request(
            'http://watchtower:8080/v1/update',
            method='POST',
            data=b'',
            headers={'Authorization': f'Bearer {token}'},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
        if status in (200, 204):
            html = (
                '<span class="text-emerald-500 text-xs font-medium block">Update triggered successfully.</span>'
                '<span class="text-xs text-muted-foreground block mt-1">'
                'celery &amp; celery-beat will restart automatically. '
                'To complete the update, manually restart <strong>homedash-web-1</strong> in Portainer.</span>'
            )
        else:
            html = f'<span class="text-destructive text-xs">Watchtower returned status {status}.</span>'
    except Exception as exc:
        html = f'<span class="text-destructive text-xs">Could not reach Watchtower: {exc}</span>'

    return HttpResponse(html, content_type='text/html')


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


def setup_wizard(request):
    """First-run installation wizard. Only accessible when no superuser exists."""
    from django.contrib.auth.models import User
    from django.contrib.auth import login

    if User.objects.filter(is_superuser=True).exists():
        return render(request, 'setup.html', {'already_done': True})

    errors = {}
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        if not username:
            errors['username'] = 'Username is required.'
        elif User.objects.filter(username=username).exists():
            errors['username'] = 'That username is already taken.'

        if not password:
            errors['password'] = 'Password is required.'
        elif len(password) < 8:
            errors['password'] = 'Password must be at least 8 characters.'
        elif password != password2:
            errors['password2'] = 'Passwords do not match.'

        if not errors:
            user = User.objects.create_superuser(username=username, email=email, password=password)
            login(request, user)
            return render(request, 'setup.html', {'done': True, 'username': username})

    features = [
        'Real-time monitoring', 'Service dashboards',
        'Live download tracking', 'Web terminal',
        'Notification alerts', 'Proxmox VM status',
    ]
    return render(request, 'setup.html', {'errors': errors, 'post': request.POST, 'features': features})


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


def _append_traffic_point(pk, point, now):
    """Append a bytes/sec data point to all pfSense traffic time series."""
    # (key_suffix, max_points, min_seconds_between_points)
    series_cfg = [
        ('live',  60,  0),      # every poll (~5s), keep 60 → ~5 min window
        ('day',  288, 300),     # every 5 min → 24 h
        ('week', 336, 1800),    # every 30 min → 7 days
        ('month',360, 7200),    # every 2 h → 30 days
    ]
    for suffix, max_pts, min_interval in series_cfg:
        key = f'pfsense_traffic_{suffix}_{pk}'
        series = cache.get(key) or []
        if min_interval == 0 or not series or (now - series[-1]['t']) >= min_interval:
            series.append(point)
            if len(series) > max_pts:
                series = series[-max_pts:]
            cache.set(key, series, 86400 * 32)


def pfsense_traffic(request, pk):
    """JSON endpoint: fetch live WAN bytes/sec and update Redis time series.

    Called by the browser every 5 s.  Also serves accumulated series for the
    day/week/month tabs without making a new pfSense API call.
    """
    from django.shortcuts import get_object_or_404
    service = get_object_or_404(Service, pk=pk, is_active=True)
    period  = request.GET.get('period', 'live')

    now = int(_time.time())

    # Only hit pfSense API on live polls (not when switching tabs)
    if period == 'live':
        api = PfSenseAPI(service)
        iface_data = api._get('status/interfaces')
        if iface_data and iface_data.get('code') == 200:
            ifaces = iface_data.get('data') or []
            wan = next((i for i in ifaces if i.get('name') == 'wan'), None) or (ifaces[0] if ifaces else None)
            if wan:
                curr_in  = wan.get('inbytes',  0) or 0
                curr_out = wan.get('outbytes', 0) or 0
                prev_key = f'pfsense_traffic_prev_{pk}'
                prev = cache.get(prev_key)
                if prev and curr_in >= prev['in'] and curr_out >= prev['out']:
                    dt = now - prev['t']
                    if dt > 0:
                        point = {
                            't':   now,
                            'in':  int((curr_in  - prev['in'])  / dt),
                            'out': int((curr_out - prev['out']) / dt),
                        }
                        _append_traffic_point(pk, point, now)
                cache.set(prev_key, {'t': now, 'in': curr_in, 'out': curr_out}, 7200)

    series = cache.get(f'pfsense_traffic_{period}_{pk}') or []
    return JsonResponse({'series': series, 'period': period})


def service_dashboard(request, pk):
    """View for a dedicated internal dashboard for a specific service.

    This view relies on cached stats so that the page renders quickly even if
    the target service (e.g. pfSense) is experiencing latency.  Live data is
    still available by hitting the "Refresh stats" button on the page, which
    can call the helper with `force_live=True` if you add that feature later.
    """
    from django.shortcuts import get_object_or_404
    service = get_object_or_404(Service, pk=pk, is_active=True)

    stats = _get_stats(service)

    template_name = f'dashboards/{service.service_type}.html'
    from django.template.loader import get_template
    from django.template import TemplateDoesNotExist
    try:
        get_template(template_name)
    except TemplateDoesNotExist:
        template_name = 'dashboards/generic.html'

    ctx = {'service': service, 'stats': stats}
    if service.service_type == 'pfsense':
        ctx['traffic_periods'] = [('live','Live'),('day','24h'),('week','7d'),('month','30d')]
    return render(request, template_name, ctx)
