from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import Service
from .forms import ServiceForm
from .api import RadarrAPI, SonarrAPI, ServiceAPI

def service_list(request):
    services = Service.objects.all().order_by('-created_at')
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
        service.delete()
        if request.headers.get('HX-Request'):
            return HttpResponse("") # Removes the element from the DOM
        return redirect('service_list')
    return render(request, 'services/service_confirm_delete.html', {'service': service})

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
