from django.db import models
from django.utils import timezone
from .encryption import encrypt_value, decrypt_value

class ServiceType(models.TextChoices):
    TRUENAS = 'truenas', 'TrueNAS'
    RADARR = 'radarr', 'Radarr'
    SONARR = 'sonarr', 'Sonarr'
    OVERSEERR = 'overseerr', 'Overseerr'
    JDOWNLOADER = 'jdownloader', 'JDownloader'
    PLEX = 'plex', 'Plex'
    QBITTORRENT = 'qbittorrent', 'qBittorrent'
    TAUTULLI = 'tautulli', 'Tautulli'
    PROWLARR = 'prowlarr', 'Prowlarr'
    BAZARR = 'bazarr', 'Bazarr'
    PROXMOX = 'proxmox', 'Proxmox'
    OTHER = 'other', 'Other'

class Service(models.Model):
    name = models.CharField(max_length=100)
    service_type = models.CharField(max_length=50, choices=ServiceType.choices)
    url = models.URLField(help_text="Full base URL (e.g., http://192.168.1.100:8989)")
    
    # Store API keys or passwords securely
    api_key_encrypted = models.TextField(blank=True, null=True, help_text="Stored encrypted in the database.")
    username = models.CharField(max_length=100, blank=True, null=True, help_text="For services that require basic auth instead of an API key.")
    password_encrypted = models.TextField(blank=True, null=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Monitoring status (cached lightly in DB, but real-time in redis)
    is_online = models.BooleanField(default=False)
    last_checked = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.get_service_type_display()})"

    @property
    def api_key(self):
        return decrypt_value(self.api_key_encrypted) if self.api_key_encrypted else ""

    @api_key.setter
    def api_key(self, value):
        self.api_key_encrypted = encrypt_value(value) if value else ""

    @property
    def password(self):
        return decrypt_value(self.password_encrypted) if self.password_encrypted else ""

    @password.setter
    def password(self, value):
        self.password_encrypted = encrypt_value(value) if value else ""

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
