from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0004_alter_service_service_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='service',
            name='service_type',
            field=models.CharField(
                choices=[
                    ('truenas', 'TrueNAS'),
                    ('radarr', 'Radarr'),
                    ('sonarr', 'Sonarr'),
                    ('overseerr', 'Overseerr'),
                    ('jdownloader', 'JDownloader'),
                    ('plex', 'Plex'),
                    ('qbittorrent', 'qBittorrent'),
                    ('tautulli', 'Tautulli'),
                    ('prowlarr', 'Prowlarr'),
                    ('bazarr', 'Bazarr'),
                    ('proxmox', 'Proxmox'),
                    ('pfsense', 'pfSense'),
                    ('homedash', 'HomeDash'),
                    ('other', 'Other'),
                ],
                max_length=50,
            ),
        ),
    ]
