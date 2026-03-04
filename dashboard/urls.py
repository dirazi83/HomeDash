from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('widget/<int:pk>/', views.widget_update, name='widget_update'),
    path('service/<int:pk>/', views.service_dashboard, name='service_dashboard'),
    path('service/<int:pk>/jd-live/', views.jdownloader_live, name='jdownloader_live'),
    path('service/<int:pk>/qb-live/', views.qbittorrent_live, name='qbittorrent_live'),
    path('service/<int:pk>/proxmox-live/', views.proxmox_live, name='proxmox_live'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/trigger-poll/', views.settings_trigger_poll, name='settings_trigger_poll'),
    path('settings/clear-cache/', views.settings_clear_cache, name='settings_clear_cache'),
    path('terminal/', views.terminal_page, name='terminal'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/dot/', views.notifications_dot, name='notifications_dot'),
]
