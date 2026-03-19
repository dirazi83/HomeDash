from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import Service
from .forms import ServiceForm
from .api import RadarrAPI, SonarrAPI, ServiceAPI

def service_list(request):
    # only show active entries by default; disabled services can be re‑enabled
    services = Service.objects.filter(is_active=True).order_by('-created_at')
    return render(request, 'services/service_list.html', {'services': services})

def service_add(request):
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save()
            return redirect('service_list')
    else:
        form = ServiceForm()
    
    # If it's an HTMX request, render just the form partial
    if request.headers.get('HX-Request'):
        return render(request, 'services/partials/service_form.html', {'form': form})
    
    return render(request, 'services/service_add_edit.html', {'form': form, 'title': 'Add New Service'})

def service_edit(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        form = ServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            return redirect('service_list')
    else:
        # We don't populate the api_key field for security reasons, it remains blank to keep it unchanged if not provided.
        form = ServiceForm(instance=service)
        
    if request.headers.get('HX-Request'):
        return render(request, 'services/partials/service_form.html', {'form': form, 'service': service})
        
    return render(request, 'services/service_add_edit.html', {'form': form, 'service': service, 'title': f'Edit {service.name}'})

def service_delete(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == 'POST':
        # remember pk ahead of time for cache clearing
        svc_pk = service.pk
        # mark inactive first so the UI will hide even if deletion fails
        service.is_active = False
        service.save(update_fields=["is_active"])
        try:
            service.delete()
        except Exception:
            # if deletion errors (e.g. DB locked), ignoring ensures we still
            # hide the service; it can be cleaned up later with a management
            # command or manually via the admin interface.
            pass

        # remove any stale cached stats as well
        from django.core.cache import cache as _cache
        _cache.delete(f"service_stats_{svc_pk}")

        if request.headers.get('HX-Request'):
            resp = HttpResponse("")
            resp["HX-Trigger"] = "serviceDeleted"
            return resp
        return redirect('service_list')
    return render(request, 'services/service_confirm_delete.html', {'service': service})

def terminal_exec(request):
    """Execute a shell command and return an HTML output snippet."""
    if request.method != 'POST':
        return HttpResponse(status=405)
    import subprocess
    command = request.POST.get('command', '').strip()
    if not command:
        return HttpResponse('')
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30,
            cwd='/root/HomeDashboard',
        )
        stdout = result.stdout
        stderr = result.stderr
        exit_code = result.returncode
    except subprocess.TimeoutExpired:
        stdout = ''
        stderr = 'Command timed out (30s limit).'
        exit_code = -1
    except Exception as exc:
        stdout = ''
        stderr = str(exc)
        exit_code = -1
    return render(request, 'services/partials/terminal_output.html', {
        'command': command,
        'stdout': stdout,
        'stderr': stderr,
        'exit_code': exit_code,
    })


def service_test_connection(request, pk):
    service = get_object_or_404(Service, pk=pk)
    
    # Select appropriate API tester
    if service.service_type == 'radarr':
        api = RadarrAPI(service)
    elif service.service_type == 'sonarr':
        api = SonarrAPI(service)
    else:
        api = ServiceAPI(service)
        
    is_online = api.test_connection()
    
    # Return HTML fragment for HTMX to swap
    return render(request, 'services/partials/status_badge.html', {'service': service})


def service_backup(request):
    """Return a JSON dump of all services (for backup)."""
    # note: encrypted fields are exported as-is so they can be restored later
    services = list(Service.objects.values(
        'name', 'service_type', 'url',
        'api_key_encrypted', 'username', 'password_encrypted',
        'is_active'
    ))
    from django.http import JsonResponse
    resp = JsonResponse(services, safe=False)
    resp['Content-Disposition'] = 'attachment; filename=services_backup.json'
    return resp


def service_restore(request):
    """Import services from a previously generated JSON dump.

    Existing services are matched on (name, service_type) and updated; new
    entries are created.  Any encrypted fields are preserved verbatim so the
    administrator must ensure the backup has not been tampered with.
    """
    if request.method == 'POST':
        fileobj = request.FILES.get('backup_file')
        if fileobj:
            import json
            try:
                data = json.load(fileobj)
            except Exception:
                return render(request, 'services/service_backup_restore.html', {
                    'error': 'Invalid JSON file.'
                })
            for row in data:
                defaults = {
                    'url': row.get('url'),
                    'api_key_encrypted': row.get('api_key_encrypted'),
                    'username': row.get('username'),
                    'password_encrypted': row.get('password_encrypted'),
                    'is_active': row.get('is_active', True),
                }
                Service.objects.update_or_create(
                    name=row.get('name'),
                    service_type=row.get('service_type'),
                    defaults=defaults,
                )
            return redirect('service_list')
    return render(request, 'services/service_backup_restore.html')

