from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('widget/<int:pk>/', views.widget_update, name='widget_update'),
    path('service/<int:pk>/', views.service_dashboard, name='service_dashboard'),
    path('service/<int:pk>/jd-live/', views.jdownloader_live, name='jdownloader_live'),
    path('service/<int:pk>/qb-live/', views.qbittorrent_live, name='qbittorrent_live'),
    path('service/<int:pk>/proxmox-live/', views.proxmox_live, name='proxmox_live'),
    path('service/<int:pk>/pfsense-traffic/', views.pfsense_traffic, name='pfsense_traffic'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/trigger-poll/', views.settings_trigger_poll, name='settings_trigger_poll'),
    path('settings/clear-cache/', views.settings_clear_cache, name='settings_clear_cache'),
    path('settings/backup/', views.settings_backup, name='settings_backup'),
    path('settings/restore/', views.settings_restore, name='settings_restore'),
    path('settings/check-update/', views.settings_check_update, name='settings_check_update'),
    path('settings/apply-update/', views.settings_apply_update, name='settings_apply_update'),
    path('setup/', views.setup_wizard, name='setup'),
    path('terminal/', views.terminal_page, name='terminal'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/dot/', views.notifications_dot, name='notifications_dot'),
]
