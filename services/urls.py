from django.urls import path
from . import views, radarr_views

urlpatterns = [
    path('', views.service_list, name='service_list'),
    path('add/', views.service_add, name='service_add'),
    path('<int:pk>/edit/', views.service_edit, name='service_edit'),
    path('<int:pk>/delete/', views.service_delete, name='service_delete'),
    path('<int:pk>/test/', views.service_test_connection, name='service_test'),

    # Radarr-specific endpoints
    path('<int:service_pk>/radarr/movies/', radarr_views.radarr_movies_list, name='radarr_movies'),
    path('<int:service_pk>/radarr/movies/<int:movie_id>/', radarr_views.radarr_movie_detail, name='radarr_movie_detail'),
    path('<int:service_pk>/radarr/movies/search/', radarr_views.radarr_movie_search, name='radarr_movie_search'),
    path('<int:service_pk>/radarr/movies/add/', radarr_views.radarr_movie_add, name='radarr_movie_add'),
    path('<int:service_pk>/radarr/movies/<int:movie_id>/update/', radarr_views.radarr_movie_update, name='radarr_movie_update'),
    path('<int:service_pk>/radarr/movies/<int:movie_id>/delete/', radarr_views.radarr_movie_delete, name='radarr_movie_delete'),

    path('<int:service_pk>/radarr/queue/', radarr_views.radarr_queue, name='radarr_queue'),
    path('<int:service_pk>/radarr/queue/<int:queue_id>/delete/', radarr_views.radarr_queue_delete, name='radarr_queue_delete'),

    path('<int:service_pk>/radarr/calendar/', radarr_views.radarr_calendar, name='radarr_calendar'),
    path('<int:service_pk>/radarr/history/', radarr_views.radarr_history, name='radarr_history'),
    path('<int:service_pk>/radarr/missing/', radarr_views.radarr_missing, name='radarr_missing'),

    path('<int:service_pk>/radarr/system/', radarr_views.radarr_system_status, name='radarr_system'),
    path('<int:service_pk>/radarr/quality-profiles/', radarr_views.radarr_quality_profiles, name='radarr_quality_profiles'),
    path('<int:service_pk>/radarr/root-folders/', radarr_views.radarr_root_folders, name='radarr_root_folders'),

    path('<int:service_pk>/radarr/command/', radarr_views.radarr_command, name='radarr_command'),
]
