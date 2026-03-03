"""
Views for Radarr-specific operations and API interactions.
"""
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from .models import Service
from .api import RadarrAPI
import json


# =========================
# MOVIE MANAGEMENT VIEWS
# =========================

@require_http_methods(["GET"])
def radarr_movies_list(request, service_pk):
    """Get all movies for a Radarr service."""
    service = get_object_or_404(Service, pk=service_pk, service_type='radarr')
    api = RadarrAPI(service)

    # Check cache first
    cache_key = f"radarr_movies_{service_pk}"
    movies = cache.get(cache_key)

    if movies is None:
        movies = api.get_movies()
        if movies:
            cache.set(cache_key, movies, timeout=300)  # Cache for 5 minutes

    if request.headers.get('HX-Request'):
        return render(request, 'services/radarr/partials/movies_list.html', {
            'movies': movies,
            'service': service
        })

    return JsonResponse({'movies': movies or []})


@require_http_methods(["GET"])
def radarr_movie_detail(request, service_pk, movie_id):
    """Get details for a specific movie."""
    service = get_object_or_404(Service, pk=service_pk, service_type='radarr')
    api = RadarrAPI(service)

    movie = api.get_movie(movie_id)

    if request.headers.get('HX-Request'):
        return render(request, 'services/radarr/partials/movie_detail.html', {
            'movie': movie,
            'service': service
        })

    return JsonResponse({'movie': movie})


@require_http_methods(["POST"])
def radarr_movie_search(request, service_pk):
    """Search for movies to add to Radarr."""
    service = get_object_or_404(Service, pk=service_pk, service_type='radarr')
    api = RadarrAPI(service)

    search_term = request.POST.get('term', request.GET.get('term', ''))

    if not search_term:
        return JsonResponse({'error': 'Search term required'}, status=400)

    results = api.search_movies(search_term)

    if request.headers.get('HX-Request'):
        return render(request, 'services/radarr/partials/movie_search_results.html', {
            'results': results,
            'service': service
        })

    return JsonResponse({'results': results or []})


@require_http_methods(["POST"])
def radarr_movie_add(request, service_pk):
    """Add a new movie to Radarr."""
    service = get_object_or_404(Service, pk=service_pk, service_type='radarr')
    api = RadarrAPI(service)

    try:
        data = json.loads(request.body)
        result = api.add_movie(data)

        # Invalidate movies cache
        cache.delete(f"radarr_movies_{service_pk}")
        cache.delete(f"service_stats_{service_pk}")

        if result:
            return JsonResponse({'success': True, 'movie': result})
        else:
            return JsonResponse({'success': False, 'error': 'Failed to add movie'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
def radarr_movie_update(request, service_pk, movie_id):
    """Update a movie in Radarr."""
    service = get_object_or_404(Service, pk=service_pk, service_type='radarr')
    api = RadarrAPI(service)

    try:
        data = json.loads(request.body)
        result = api.update_movie(movie_id, data)

        # Invalidate cache
        cache.delete(f"radarr_movies_{service_pk}")
        cache.delete(f"service_stats_{service_pk}")

        if result:
            return JsonResponse({'success': True, 'movie': result})
        else:
            return JsonResponse({'success': False, 'error': 'Failed to update movie'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST", "DELETE"])
def radarr_movie_delete(request, service_pk, movie_id):
    """Delete a movie from Radarr."""
    service = get_object_or_404(Service, pk=service_pk, service_type='radarr')
    api = RadarrAPI(service)

    delete_files = request.POST.get('deleteFiles', 'false').lower() == 'true'
    add_exclusion = request.POST.get('addExclusion', 'false').lower() == 'true'

    success = api.delete_movie(movie_id, delete_files, add_exclusion)

    # Invalidate cache
    cache.delete(f"radarr_movies_{service_pk}")
    cache.delete(f"service_stats_{service_pk}")

    if success:
        if request.headers.get('HX-Request'):
            return HttpResponse("")  # Return empty to remove from DOM
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'error': 'Failed to delete movie'}, status=400)


# =========================
# QUEUE MANAGEMENT VIEWS
# =========================

@require_http_methods(["GET"])
def radarr_queue(request, service_pk):
    """Get the download queue."""
    service = get_object_or_404(Service, pk=service_pk, service_type='radarr')
    api = RadarrAPI(service)

    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('pageSize', 20))

    queue_data = api.get_queue(page=page, page_size=page_size)

    if request.headers.get('HX-Request'):
        return render(request, 'services/radarr/partials/queue_list.html', {
            'queue': queue_data,
            'service': service
        })

    return JsonResponse(queue_data or {})


@require_http_methods(["DELETE", "POST"])
def radarr_queue_delete(request, service_pk, queue_id):
    """Remove an item from the queue."""
    service = get_object_or_404(Service, pk=service_pk, service_type='radarr')
    api = RadarrAPI(service)

    remove_from_client = request.POST.get('removeFromClient', 'true').lower() == 'true'
    blocklist = request.POST.get('blocklist', 'true').lower() == 'true'

    success = api.delete_queue_item(queue_id, remove_from_client, blocklist)

    # Invalidate cache
    cache.delete(f"service_stats_{service_pk}")

    if success:
        if request.headers.get('HX-Request'):
            return HttpResponse("")  # Remove from DOM
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'error': 'Failed to delete queue item'}, status=400)


# =========================
# CALENDAR & HISTORY VIEWS
# =========================

@require_http_methods(["GET"])
def radarr_calendar(request, service_pk):
    """Get calendar of upcoming movies."""
    service = get_object_or_404(Service, pk=service_pk, service_type='radarr')
    api = RadarrAPI(service)

    start_date = request.GET.get('start')
    end_date = request.GET.get('end')

    calendar = api.get_calendar(start_date, end_date)

    if request.headers.get('HX-Request'):
        return render(request, 'services/radarr/partials/calendar.html', {
            'calendar': calendar,
            'service': service
        })

    return JsonResponse({'calendar': calendar or []})


@require_http_methods(["GET"])
def radarr_history(request, service_pk):
    """Get download/activity history."""
    service = get_object_or_404(Service, pk=service_pk, service_type='radarr')
    api = RadarrAPI(service)

    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('pageSize', 20))
    movie_id = request.GET.get('movieId')

    history_data = api.get_history(
        page=page,
        page_size=page_size,
        movie_id=int(movie_id) if movie_id else None
    )

    if request.headers.get('HX-Request'):
        return render(request, 'services/radarr/partials/history.html', {
            'history': history_data,
            'service': service
        })

    return JsonResponse(history_data or {})


# =========================
# WANTED (MISSING) VIEWS
# =========================

@require_http_methods(["GET"])
def radarr_missing(request, service_pk):
    """Get missing (wanted but not downloaded) movies."""
    service = get_object_or_404(Service, pk=service_pk, service_type='radarr')
    api = RadarrAPI(service)

    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('pageSize', 20))

    missing_data = api.get_missing_movies(page=page, page_size=page_size)

    if request.headers.get('HX-Request'):
        return render(request, 'services/radarr/partials/missing_movies.html', {
            'missing': missing_data,
            'service': service
        })

    return JsonResponse(missing_data or {})


# =========================
# SYSTEM INFO VIEWS
# =========================

@require_http_methods(["GET"])
def radarr_system_status(request, service_pk):
    """Get system status and information."""
    service = get_object_or_404(Service, pk=service_pk, service_type='radarr')
    api = RadarrAPI(service)

    status = api.get_system_status()
    disk_space = api.get_disk_space()
    health = api.get_health()

    data = {
        'status': status,
        'diskSpace': disk_space,
        'health': health
    }

    if request.headers.get('HX-Request'):
        return render(request, 'services/radarr/partials/system_info.html', {
            'data': data,
            'service': service
        })

    return JsonResponse(data)


@require_http_methods(["GET"])
def radarr_quality_profiles(request, service_pk):
    """Get quality profiles."""
    service = get_object_or_404(Service, pk=service_pk, service_type='radarr')
    api = RadarrAPI(service)

    profiles = api.get_quality_profiles()

    return JsonResponse({'profiles': profiles or []})


@require_http_methods(["GET"])
def radarr_root_folders(request, service_pk):
    """Get root folders."""
    service = get_object_or_404(Service, pk=service_pk, service_type='radarr')
    api = RadarrAPI(service)

    folders = api.get_root_folders()

    return JsonResponse({'folders': folders or []})


# =========================
# COMMAND VIEWS
# =========================

@require_http_methods(["POST"])
def radarr_command(request, service_pk):
    """Execute a Radarr command."""
    service = get_object_or_404(Service, pk=service_pk, service_type='radarr')
    api = RadarrAPI(service)

    try:
        data = json.loads(request.body)
        command_name = data.pop('name')
        result = api.run_command(command_name, **data)

        if result:
            return JsonResponse({'success': True, 'command': result})
        else:
            return JsonResponse({'success': False, 'error': 'Command failed'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
