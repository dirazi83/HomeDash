import requests
from django.utils import timezone
from .models import Service, ServiceType
from typing import Optional, Dict, List, Any

try:
    import myjdapi as _myjdapi
    MYJDAPI_AVAILABLE = True
except ImportError:
    MYJDAPI_AVAILABLE = False

# qBittorrent torrent state → (human label, Tailwind colour class)
QB_STATE_MAP = {
    'downloading':        ('Downloading',    'text-emerald-500'),
    'uploading':          ('Seeding',        'text-blue-500'),
    'stalledDL':          ('Stalled ↓',      'text-yellow-500'),
    'stalledUP':          ('Stalled ↑',      'text-blue-400'),
    'checkingUP':         ('Checking',       'text-sky-500'),
    'checkingDL':         ('Checking',       'text-sky-500'),
    'checkingResumeData': ('Checking',       'text-sky-500'),
    'pausedDL':           ('Paused',         'text-muted-foreground'),
    'pausedUP':           ('Completed',      'text-blue-500'),
    'queuedDL':           ('Queued',         'text-yellow-400'),
    'queuedUP':           ('Queued',         'text-yellow-400'),
    'error':              ('Error',          'text-destructive'),
    'missingFiles':       ('Missing Files',  'text-destructive'),
    'allocating':         ('Allocating',     'text-muted-foreground'),
    'metaDL':             ('Fetching Meta',  'text-sky-400'),
    'forcedDL':           ('Forced DL',      'text-emerald-400'),
    'forcedUP':           ('Forced Seed',    'text-blue-400'),
    'moving':             ('Moving',         'text-sky-400'),
    'unknown':            ('Unknown',        'text-muted-foreground'),
}

class ServiceAPI:
    """Base class for all service APIs."""
    def __init__(self, service: Service):
        self.service = service
        self.base_url = service.url.rstrip('/')
        self.api_key = service.api_key

    def test_connection(self) -> bool:
        """Override in subclasses or test basic connectivity here."""
        try:
            response = requests.get(self.base_url, timeout=5)
            # Even a 401 Unauthorized means the port / server is responding
            is_online = response.status_code < 500
        except requests.RequestException:
            is_online = False

        self.service.is_online = is_online
        self.service.last_checked = timezone.now()
        self.service.save()
        return is_online

    def fetch_stats(self) -> dict:
        """Fetch full stats payload to cache."""
        return {'is_online': self.test_connection()}

class RadarrAPI(ServiceAPI):
    """Comprehensive Radarr v3 API Client with full endpoint support."""

    def __init__(self, service: Service):
        super().__init__(service)
        self.headers = {"X-Api-Key": self.api_key}

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Generic API request handler."""
        url = f"{self.base_url}/api/v3/{endpoint.lstrip('/')}"
        kwargs['headers'] = self.headers
        kwargs.setdefault('timeout', 10)

        try:
            response = requests.request(method, url, **kwargs)
            if response.ok:
                return response.json() if response.content else {}
            return None
        except requests.RequestException:
            return None

    def test_connection(self) -> bool:
        try:
            url = f"{self.base_url}/api/v3/system/status"
            response = requests.get(url, headers=self.headers, timeout=5)
            is_online = response.ok
        except requests.RequestException:
            is_online = False

        self.service.is_online = is_online
        self.service.last_checked = timezone.now()
        self.service.save()
        return is_online

    def fetch_stats(self) -> dict:
        """Fetch enhanced stats with disk space and upcoming movies."""
        stats = {
            'is_online': self.test_connection(),
            'version': None,
            'total_movies': 0,
            'downloaded_movies': 0,
            'monitored_movies': 0,
            'queue_size': 0,
            'disk_space': [],
            'missing_movies': 0,
            'upcoming_movies': []
        }

        if not stats['is_online']:
            return stats

        try:
            # System Status
            status = self._request('GET', 'system/status')
            if status:
                stats['version'] = status.get('version', '')

            # Queue
            queue = self._request('GET', 'queue')
            if queue:
                stats['queue_size'] = queue.get('totalRecords', len(queue.get('records', [])))

            # Movies
            movies = self._request('GET', 'movie')
            if movies:
                stats['total_movies'] = len(movies)
                stats['downloaded_movies'] = sum(1 for m in movies if m.get('hasFile', False))
                stats['monitored_movies'] = sum(1 for m in movies if m.get('monitored', False))

            # Disk Space
            disk_space = self._request('GET', 'diskspace')
            if disk_space:
                stats['disk_space'] = disk_space

            # Calendar (Upcoming movies - next 30 days)
            from datetime import datetime, timedelta
            start_date = datetime.now().strftime('%Y-%m-%d')
            end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            calendar = self._request('GET', f'calendar?start={start_date}&end={end_date}')
            if calendar:
                stats['upcoming_movies'] = calendar[:5]  # Top 5

            # Missing movies count
            wanted = self._request('GET', 'wanted/missing?pageSize=1')
            if wanted:
                stats['missing_movies'] = wanted.get('totalRecords', 0)

        except Exception:
            pass

        return stats

    # =========================
    # MOVIE MANAGEMENT
    # =========================

    def get_movies(self, tmdb_id: Optional[int] = None) -> List[Dict]:
        """Get all movies or a specific movie by TMDB ID."""
        if tmdb_id:
            result = self._request('GET', f'movie?tmdbId={tmdb_id}')
            return result if isinstance(result, list) else []
        result = self._request('GET', 'movie')
        return result if result else []

    def get_movie(self, movie_id: int) -> Optional[Dict]:
        """Get a specific movie by Radarr internal ID."""
        return self._request('GET', f'movie/{movie_id}')

    def add_movie(self, movie_data: Dict) -> Optional[Dict]:
        """
        Add a new movie to Radarr.

        Args:
            movie_data: Dict containing movie information including:
                - title, year, tmdbId, qualityProfileId, rootFolderPath, monitored, etc.
        """
        return self._request('POST', 'movie', json=movie_data)

    def update_movie(self, movie_id: int, movie_data: Dict) -> Optional[Dict]:
        """Update an existing movie."""
        return self._request('PUT', f'movie/{movie_id}', json=movie_data)

    def delete_movie(self, movie_id: int, delete_files: bool = False,
                     add_exclusion: bool = False) -> bool:
        """
        Delete a movie from Radarr.

        Args:
            movie_id: Radarr internal movie ID
            delete_files: Whether to delete movie files from disk
            add_exclusion: Whether to add to import exclusion list
        """
        params = {
            'deleteFiles': str(delete_files).lower(),
            'addImportExclusion': str(add_exclusion).lower()
        }
        result = self._request('DELETE', f'movie/{movie_id}', params=params)
        return result is not None

    def search_movies(self, term: str) -> List[Dict]:
        """Search for movies using TMDB/IMDB lookup."""
        result = self._request('GET', f'movie/lookup?term={term}')
        return result if result else []

    def lookup_movie_by_tmdb(self, tmdb_id: int) -> Optional[Dict]:
        """Lookup a movie by TMDB ID."""
        return self._request('GET', f'movie/lookup/tmdb?tmdbId={tmdb_id}')

    def lookup_movie_by_imdb(self, imdb_id: str) -> Optional[Dict]:
        """Lookup a movie by IMDB ID."""
        return self._request('GET', f'movie/lookup/imdb?imdbId={imdb_id}')

    # =========================
    # QUEUE MANAGEMENT
    # =========================

    def get_queue(self, page: int = 1, page_size: int = 20,
                  sort_key: str = 'timeleft', sort_dir: str = 'asc') -> Optional[Dict]:
        """Get the download queue with pagination."""
        params = {
            'page': page,
            'pageSize': page_size,
            'sortKey': sort_key,
            'sortDirection': sort_dir
        }
        return self._request('GET', 'queue', params=params)

    def get_queue_details(self, movie_id: Optional[int] = None) -> List[Dict]:
        """Get queue details, optionally filtered by movie ID."""
        endpoint = f'queue/details?movieId={movie_id}' if movie_id else 'queue/details'
        result = self._request('GET', endpoint)
        return result if result else []

    def get_queue_status(self) -> Optional[Dict]:
        """Get queue status summary."""
        return self._request('GET', 'queue/status')

    def delete_queue_item(self, queue_id: int, remove_from_client: bool = True,
                         blocklist: bool = True) -> bool:
        """Remove an item from the queue."""
        params = {
            'removeFromClient': str(remove_from_client).lower(),
            'blocklist': str(blocklist).lower()
        }
        result = self._request('DELETE', f'queue/{queue_id}', params=params)
        return result is not None

    def grab_release(self, queue_id: int) -> Optional[Dict]:
        """Force grab/download a release from the queue."""
        return self._request('POST', f'queue/grab/{queue_id}')

    # =========================
    # CALENDAR & HISTORY
    # =========================

    def get_calendar(self, start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> List[Dict]:
        """
        Get calendar of movies.

        Args:
            start_date: ISO date string (YYYY-MM-DD)
            end_date: ISO date string (YYYY-MM-DD)
        """
        params = {}
        if start_date:
            params['start'] = start_date
        if end_date:
            params['end'] = end_date

        result = self._request('GET', 'calendar', params=params)
        return result if result else []

    def get_history(self, page: int = 1, page_size: int = 20,
                    sort_key: str = 'date', sort_dir: str = 'desc',
                    movie_id: Optional[int] = None) -> Optional[Dict]:
        """Get history with pagination."""
        params = {
            'page': page,
            'pageSize': page_size,
            'sortKey': sort_key,
            'sortDirection': sort_dir
        }
        if movie_id:
            params['movieId'] = movie_id

        return self._request('GET', 'history', params=params)

    def get_history_since(self, date: str, movie_id: Optional[int] = None) -> List[Dict]:
        """Get history since a specific date."""
        params = {'date': date}
        if movie_id:
            params['movieId'] = movie_id
        result = self._request('GET', 'history/since', params=params)
        return result if result else []

    # =========================
    # WANTED (MISSING/CUTOFF)
    # =========================

    def get_missing_movies(self, page: int = 1, page_size: int = 20,
                          sort_key: str = 'title') -> Optional[Dict]:
        """Get missing (wanted but not downloaded) movies."""
        params = {
            'page': page,
            'pageSize': page_size,
            'sortKey': sort_key
        }
        return self._request('GET', 'wanted/missing', params=params)

    def get_cutoff_unmet(self, page: int = 1, page_size: int = 20) -> Optional[Dict]:
        """Get movies that haven't met the cutoff quality."""
        params = {'page': page, 'pageSize': page_size}
        return self._request('GET', 'wanted/cutoff', params=params)

    # =========================
    # RELEASES (INDEXER SEARCH)
    # =========================

    def search_releases(self, movie_id: int) -> List[Dict]:
        """Search for releases for a specific movie."""
        result = self._request('GET', f'release?movieId={movie_id}')
        return result if result else []

    def download_release(self, guid: str, indexer_id: int) -> Optional[Dict]:
        """Download a specific release."""
        data = {'guid': guid, 'indexerId': indexer_id}
        return self._request('POST', 'release', json=data)

    # =========================
    # QUALITY PROFILES
    # =========================

    def get_quality_profiles(self) -> List[Dict]:
        """Get all quality profiles."""
        result = self._request('GET', 'qualityprofile')
        return result if result else []

    def get_quality_profile(self, profile_id: int) -> Optional[Dict]:
        """Get a specific quality profile."""
        return self._request('GET', f'qualityprofile/{profile_id}')

    # =========================
    # ROOT FOLDERS
    # =========================

    def get_root_folders(self) -> List[Dict]:
        """Get all root folders."""
        result = self._request('GET', 'rootfolder')
        return result if result else []

    def add_root_folder(self, path: str) -> Optional[Dict]:
        """Add a new root folder."""
        return self._request('POST', 'rootfolder', json={'path': path})

    def delete_root_folder(self, folder_id: int) -> bool:
        """Delete a root folder."""
        result = self._request('DELETE', f'rootfolder/{folder_id}')
        return result is not None

    # =========================
    # SYSTEM & COMMANDS
    # =========================

    def get_system_status(self) -> Optional[Dict]:
        """Get system status information."""
        return self._request('GET', 'system/status')

    def get_disk_space(self) -> List[Dict]:
        """Get disk space information."""
        result = self._request('GET', 'diskspace')
        return result if result else []

    def get_health(self) -> List[Dict]:
        """Get system health checks."""
        result = self._request('GET', 'health')
        return result if result else []

    def get_tasks(self) -> List[Dict]:
        """Get scheduled tasks."""
        result = self._request('GET', 'system/task')
        return result if result else []

    def run_command(self, command_name: str, **kwargs) -> Optional[Dict]:
        """
        Execute a command.

        Common commands:
        - RescanMovie (movieId)
        - RefreshMovie (movieId)
        - MoviesSearch (movieIds: [])
        - DownloadedMoviesScan
        - RssSync
        - Backup
        """
        data = {'name': command_name, **kwargs}
        return self._request('POST', 'command', json=data)

    def get_commands(self) -> List[Dict]:
        """Get all running and queued commands."""
        result = self._request('GET', 'command')
        return result if result else []

    def get_command(self, command_id: int) -> Optional[Dict]:
        """Get status of a specific command."""
        return self._request('GET', f'command/{command_id}')

    # =========================
    # TAGS
    # =========================

    def get_tags(self) -> List[Dict]:
        """Get all tags."""
        result = self._request('GET', 'tag')
        return result if result else []

    def create_tag(self, label: str) -> Optional[Dict]:
        """Create a new tag."""
        return self._request('POST', 'tag', json={'label': label})

    def delete_tag(self, tag_id: int) -> bool:
        """Delete a tag."""
        result = self._request('DELETE', f'tag/{tag_id}')
        return result is not None

class SonarrAPI(ServiceAPI):
    """Comprehensive Sonarr v3 API Client with full endpoint support."""

    def __init__(self, service: Service):
        super().__init__(service)
        self.headers = {"X-Api-Key": self.api_key}

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Generic API request handler."""
        url = f"{self.base_url}/api/v3/{endpoint.lstrip('/')}"
        kwargs['headers'] = self.headers
        kwargs.setdefault('timeout', 10)

        try:
            response = requests.request(method, url, **kwargs)
            if response.ok:
                return response.json() if response.content else {}
            return None
        except requests.RequestException:
            return None

    def test_connection(self) -> bool:
        try:
            url = f"{self.base_url}/api/v3/system/status"
            response = requests.get(url, headers=self.headers, timeout=5)
            is_online = response.ok
        except requests.RequestException:
            is_online = False

        self.service.is_online = is_online
        self.service.last_checked = timezone.now()
        self.service.save()
        return is_online

    def fetch_stats(self) -> dict:
        """Fetch enhanced stats for Sonarr."""
        stats = {
            'is_online': self.test_connection(),
            'version': None,
            'total_series': 0,
            'total_episodes': 0,
            'monitored_series': 0,
            'downloaded_episodes': 0,
            'queue_size': 0,
            'disk_space': [],
            'missing_episodes': 0,
            'upcoming_episodes': []
        }

        if not stats['is_online']:
            return stats

        try:
            # System Status
            status = self._request('GET', 'system/status')
            if status:
                stats['version'] = status.get('version', '')

            # Queue
            queue = self._request('GET', 'queue')
            if queue:
                stats['queue_size'] = queue.get('totalRecords', len(queue.get('records', [])))

            # Series
            series = self._request('GET', 'series')
            if series:
                stats['total_series'] = len(series)
                stats['monitored_series'] = sum(1 for s in series if s.get('monitored', False))
                stats['total_episodes'] = sum(s.get('statistics', {}).get('episodeCount', 0) for s in series)
                stats['downloaded_episodes'] = sum(s.get('statistics', {}).get('episodeFileCount', 0) for s in series)

            # Disk Space
            disk_space = self._request('GET', 'diskspace')
            if disk_space:
                stats['disk_space'] = disk_space

            # Calendar (Upcoming episodes - next 7 days)
            from datetime import datetime, timedelta
            start_date = datetime.now().strftime('%Y-%m-%d')
            end_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            calendar = self._request('GET', f'calendar?start={start_date}&end={end_date}')
            if calendar:
                stats['upcoming_episodes'] = calendar[:5]

            # Missing episodes count
            wanted = self._request('GET', 'wanted/missing?pageSize=1')
            if wanted:
                stats['missing_episodes'] = wanted.get('totalRecords', 0)

        except Exception:
            pass

        return stats

    # Series, Episode, Queue, Calendar, History, Wanted, Releases,
    # Quality Profiles, Root Folders, System, Commands, Tags methods
    # (Similar structure to RadarrAPI but adapted for TV series)

    def get_series(self, tvdb_id: Optional[int] = None) -> List[Dict]:
        """Get all series or specific by TVDB ID."""
        if tvdb_id:
            result = self._request('GET', f'series?tvdbId={tvdb_id}')
            return result if isinstance(result, list) else []
        result = self._request('GET', 'series')
        return result if result else []

    def get_series_by_id(self, series_id: int) -> Optional[Dict]:
        """Get specific series."""
        return self._request('GET', f'series/{series_id}')

    def add_series(self, series_data: Dict) -> Optional[Dict]:
        """Add new series."""
        return self._request('POST', 'series', json=series_data)

    def update_series(self, series_id: int, series_data: Dict) -> Optional[Dict]:
        """Update series."""
        return self._request('PUT', f'series/{series_id}', json=series_data)

    def delete_series(self, series_id: int, delete_files: bool = False) -> bool:
        """Delete series."""
        params = {'deleteFiles': str(delete_files).lower()}
        result = self._request('DELETE', f'series/{series_id}', params=params)
        return result is not None

    def search_series(self, term: str) -> List[Dict]:
        """Search for series."""
        result = self._request('GET', f'series/lookup?term={term}')
        return result if result else []

    def get_episodes(self, series_id: int) -> List[Dict]:
        """Get episodes for series."""
        result = self._request('GET', f'episode?seriesId={series_id}')
        return result if result else []

    def get_queue(self, page: int = 1, page_size: int = 20) -> Optional[Dict]:
        """Get download queue."""
        params = {'page': page, 'pageSize': page_size}
        return self._request('GET', 'queue', params=params)

    def delete_queue_item(self, queue_id: int, blocklist: bool = True) -> bool:
        """Remove from queue."""
        params = {'blocklist': str(blocklist).lower()}
        result = self._request('DELETE', f'queue/{queue_id}', params=params)
        return result is not None

    def get_calendar(self, start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> List[Dict]:
        """Get calendar."""
        params = {}
        if start_date:
            params['start'] = start_date
        if end_date:
            params['end'] = end_date
        result = self._request('GET', 'calendar', params=params)
        return result if result else []

    def get_history(self, page: int = 1, page_size: int = 20) -> Optional[Dict]:
        """Get history."""
        params = {'page': page, 'pageSize': page_size}
        return self._request('GET', 'history', params=params)

    def get_missing_episodes(self, page: int = 1, page_size: int = 20) -> Optional[Dict]:
        """Get missing episodes."""
        params = {'page': page, 'pageSize': page_size}
        return self._request('GET', 'wanted/missing', params=params)

    def get_quality_profiles(self) -> List[Dict]:
        """Get quality profiles."""
        result = self._request('GET', 'qualityprofile')
        return result if result else []

    def get_root_folders(self) -> List[Dict]:
        """Get root folders."""
        result = self._request('GET', 'rootfolder')
        return result if result else []

    def get_system_status(self) -> Optional[Dict]:
        """Get system status."""
        return self._request('GET', 'system/status')

    def get_disk_space(self) -> List[Dict]:
        """Get disk space."""
        result = self._request('GET', 'diskspace')
        return result if result else []

    def run_command(self, command_name: str, **kwargs) -> Optional[Dict]:
        """Execute command."""
        data = {'name': command_name, **kwargs}
        return self._request('POST', 'command', json=data)

    def get_tags(self) -> List[Dict]:
        """Get tags."""
        result = self._request('GET', 'tag')
        return result if result else []


class TrueNASAPI(ServiceAPI):
    """Comprehensive TrueNAS API Client."""

    def __init__(self, service: Service):
        super().__init__(service)
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Generic API request handler."""
        url = f"{self.base_url}/api/v2.0/{endpoint.lstrip('/')}"
        kwargs['headers'] = self.headers
        kwargs.setdefault('timeout', 10)

        try:
            response = requests.request(method, url, **kwargs)
            if response.ok:
                return response.json() if response.content else {}
            return None
        except requests.RequestException:
            return None

    def test_connection(self) -> bool:
        try:
            url = f"{self.base_url}/api/v2.0/system/info"
            response = requests.get(url, headers=self.headers, timeout=5)
            is_online = response.ok
        except requests.RequestException:
            is_online = False

        self.service.is_online = is_online
        self.service.last_checked = timezone.now()
        self.service.save()
        return is_online

    def fetch_stats(self) -> dict:
        """Fetch TrueNAS stats."""
        stats = {
            'is_online': self.test_connection(),
            'version': None,
            'hostname': None,
            'uptime': None,
            'cpu_usage': 0,
            'memory_usage': 0,
            'pools': [],
            'datasets': [],
            'alerts': []
        }

        if not stats['is_online']:
            return stats

        try:
            # System Info
            info = self._request('GET', 'system/info')
            if info:
                stats['version'] = info.get('version')
                stats['hostname'] = info.get('hostname')
                stats['uptime'] = info.get('uptime_seconds')

            # System Stats
            system_stats = self._request('GET', 'reporting/get_data', params={
                'graphs': [{'name': 'cpu'}, {'name': 'memory'}],
                'reporting.query': {'unit': 'HOUR', 'page': 1}
            })

            # Pools
            pools = self._request('GET', 'pool')
            if pools:
                stats['pools'] = [{
                    'name': p.get('name'),
                    'status': p.get('status'),
                    'size': p.get('size'),
                    'allocated': p.get('allocated'),
                    'free': p.get('free'),
                    'health': p.get('healthy')
                } for p in pools]

            # Alerts
            alerts = self._request('GET', 'alert/list')
            if alerts:
                stats['alerts'] = [{
                    'level': a.get('level'),
                    'message': a.get('formatted'),
                    'time': a.get('datetime')
                } for a in alerts[:5]]

        except Exception:
            pass

        return stats

    # Storage Management
    def get_pools(self) -> List[Dict]:
        """Get storage pools."""
        result = self._request('GET', 'pool')
        return result if result else []

    def get_pool(self, pool_id: int) -> Optional[Dict]:
        """Get specific pool."""
        return self._request('GET', f'pool/id/{pool_id}')

    def get_datasets(self, pool_name: Optional[str] = None) -> List[Dict]:
        """Get datasets."""
        endpoint = f'pool/dataset?id={pool_name}' if pool_name else 'pool/dataset'
        result = self._request('GET', endpoint)
        return result if result else []

    def create_dataset(self, name: str, pool: str, **kwargs) -> Optional[Dict]:
        """Create dataset."""
        data = {'name': f'{pool}/{name}', **kwargs}
        return self._request('POST', 'pool/dataset', json=data)

    def delete_dataset(self, dataset_id: str) -> bool:
        """Delete dataset."""
        result = self._request('DELETE', f'pool/dataset/id/{dataset_id}')
        return result is not None

    # Sharing (SMB, NFS, etc.)
    def get_smb_shares(self) -> List[Dict]:
        """Get SMB shares."""
        result = self._request('GET', 'sharing/smb')
        return result if result else []

    def create_smb_share(self, path: str, name: str, **kwargs) -> Optional[Dict]:
        """Create SMB share."""
        data = {'path': path, 'name': name, **kwargs}
        return self._request('POST', 'sharing/smb', json=data)

    def get_nfs_shares(self) -> List[Dict]:
        """Get NFS shares."""
        result = self._request('GET', 'sharing/nfs')
        return result if result else []

    # Services
    def get_services(self) -> List[Dict]:
        """Get all services."""
        result = self._request('GET', 'service')
        return result if result else []

    def start_service(self, service_name: str) -> bool:
        """Start service."""
        result = self._request('POST', f'service/start', json={'service': service_name})
        return result is not None

    def stop_service(self, service_name: str) -> bool:
        """Stop service."""
        result = self._request('POST', f'service/stop', json={'service': service_name})
        return result is not None

    # System
    def get_system_info(self) -> Optional[Dict]:
        """Get system information."""
        return self._request('GET', 'system/info')

    def get_alerts(self) -> List[Dict]:
        """Get system alerts."""
        result = self._request('GET', 'alert/list')
        return result if result else []

    def reboot(self) -> bool:
        """Reboot system."""
        result = self._request('POST', 'system/reboot')
        return result is not None

    def shutdown(self) -> bool:
        """Shutdown system."""
        result = self._request('POST', 'system/shutdown')
        return result is not None


class OverseerrAPI(ServiceAPI):
    """Comprehensive Overseerr API Client."""

    def __init__(self, service: Service):
        super().__init__(service)
        self.headers = {"X-Api-Key": self.api_key}

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Generic API request handler."""
        url = f"{self.base_url}/api/v1/{endpoint.lstrip('/')}"
        kwargs['headers'] = self.headers
        kwargs.setdefault('timeout', 10)

        try:
            response = requests.request(method, url, **kwargs)
            if response.ok:
                return response.json() if response.content else {}
            return None
        except requests.RequestException:
            return None

    def test_connection(self) -> bool:
        try:
            url = f"{self.base_url}/api/v1/status"
            response = requests.get(url, headers=self.headers, timeout=5)
            is_online = response.ok
        except requests.RequestException:
            is_online = False

        self.service.is_online = is_online
        self.service.last_checked = timezone.now()
        self.service.save()
        return is_online

    def fetch_stats(self) -> dict:
        """Fetch Overseerr stats."""
        stats = {
            'is_online': self.test_connection(),
            'version': None,
            'total_requests': 0,
            'pending_requests': 0,
            'approved_requests': 0,
            'available_requests': 0,
            'processing_requests': 0,
            'total_media': 0,
            'total_movies': 0,
            'total_series': 0,
            'recent_requests': []
        }

        if not stats['is_online']:
            return stats

        try:
            # Status
            status = self._request('GET', 'status')
            if status:
                stats['version'] = status.get('version', '')

            # Request counts
            request_count = self._request('GET', 'request/count')
            if request_count:
                stats['total_requests'] = request_count.get('total', 0)
                stats['pending_requests'] = request_count.get('pending', 0)
                stats['approved_requests'] = request_count.get('approved', 0)
                stats['available_requests'] = request_count.get('available', 0)
                stats['processing_requests'] = request_count.get('processing', 0)

            # Recent requests
            requests_data = self._request('GET', 'request?take=5&skip=0&sort=added')
            if requests_data and 'results' in requests_data:
                for req in requests_data['results']:
                    media = req.get('media') or {}
                    media_type = media.get('mediaType', '')
                    tmdb_id = media.get('tmdbId')
                    title = None
                    if tmdb_id:
                        if media_type == 'movie':
                            detail = self._request('GET', f'movie/{tmdb_id}')
                            if detail:
                                title = detail.get('title') or detail.get('originalTitle')
                        elif media_type == 'tv':
                            detail = self._request('GET', f'tv/{tmdb_id}')
                            if detail:
                                title = detail.get('name') or detail.get('originalName')
                    if not title:
                        slug = media.get('externalServiceSlug', '')
                        title = slug.replace('-', ' ').title() if slug else 'Unknown'
                    req['display_title'] = title
                stats['recent_requests'] = requests_data['results']

            # Media counts
            media_data = self._request('GET', 'media?take=1')
            if media_data:
                stats['total_media'] = media_data.get('pageInfo', {}).get('results', 0)

        except Exception:
            pass

        return stats

    # =========================
    # REQUEST MANAGEMENT
    # =========================

    def get_requests(self, take: int = 20, skip: int = 0,
                    filter_status: Optional[str] = None,
                    sort: str = 'added') -> Optional[Dict]:
        """
        Get media requests.

        Args:
            take: Number of results
            skip: Pagination offset
            filter_status: Filter by status (pending, approved, available, etc.)
            sort: Sort field
        """
        params = {'take': take, 'skip': skip, 'sort': sort}
        if filter_status:
            params['filter'] = filter_status
        return self._request('GET', 'request', params=params)

    def get_request(self, request_id: int) -> Optional[Dict]:
        """Get specific request by ID."""
        return self._request('GET', f'request/{request_id}')

    def create_request(self, media_type: str, media_id: int, **kwargs) -> Optional[Dict]:
        """
        Create new media request.

        Args:
            media_type: 'movie' or 'tv'
            media_id: TMDB/TVDB ID
            kwargs: Additional options (seasons, is4k, etc.)
        """
        data = {
            'mediaType': media_type,
            'mediaId': media_id,
            **kwargs
        }
        return self._request('POST', 'request', json=data)

    def update_request(self, request_id: int, status: str) -> Optional[Dict]:
        """
        Update request status.

        Args:
            request_id: Request ID
            status: 'approve' or 'decline'
        """
        return self._request('POST', f'request/{request_id}/{status}')

    def delete_request(self, request_id: int) -> bool:
        """Delete a request."""
        result = self._request('DELETE', f'request/{request_id}')
        return result is not None

    def retry_request(self, request_id: int) -> Optional[Dict]:
        """Retry a failed request."""
        return self._request('POST', f'request/{request_id}/retry')

    # =========================
    # MEDIA SEARCH & INFO
    # =========================

    def search_media(self, query: str, page: int = 1) -> Optional[Dict]:
        """Search for movies and TV shows."""
        params = {'query': query, 'page': page}
        return self._request('GET', 'search', params=params)

    def search_movies(self, query: str, page: int = 1) -> Optional[Dict]:
        """Search for movies only."""
        params = {'query': query, 'page': page}
        return self._request('GET', 'search/movie', params=params)

    def search_tv(self, query: str, page: int = 1) -> Optional[Dict]:
        """Search for TV shows only."""
        params = {'query': query, 'page': page}
        return self._request('GET', 'search/tv', params=params)

    def get_movie(self, movie_id: int) -> Optional[Dict]:
        """Get movie details by TMDB ID."""
        return self._request('GET', f'movie/{movie_id}')

    def get_tv(self, tv_id: int) -> Optional[Dict]:
        """Get TV show details by TMDB ID."""
        return self._request('GET', f'tv/{tv_id}')

    # =========================
    # DISCOVER & TRENDING
    # =========================

    def discover_movies(self, page: int = 1, genre: Optional[int] = None,
                       sort_by: str = 'popularity.desc') -> Optional[Dict]:
        """Discover movies."""
        params = {'page': page, 'sortBy': sort_by}
        if genre:
            params['genre'] = genre
        return self._request('GET', 'discover/movies', params=params)

    def discover_tv(self, page: int = 1, genre: Optional[int] = None,
                   sort_by: str = 'popularity.desc') -> Optional[Dict]:
        """Discover TV shows."""
        params = {'page': page, 'sortBy': sort_by}
        if genre:
            params['genre'] = genre
        return self._request('GET', 'discover/tv', params=params)

    def get_trending(self) -> Optional[Dict]:
        """Get trending media."""
        return self._request('GET', 'discover/trending')

    def get_popular_movies(self, page: int = 1) -> Optional[Dict]:
        """Get popular movies."""
        return self._request('GET', 'discover/movies/popular', params={'page': page})

    def get_popular_tv(self, page: int = 1) -> Optional[Dict]:
        """Get popular TV shows."""
        return self._request('GET', 'discover/tv/popular', params={'page': page})

    def get_upcoming_movies(self, page: int = 1) -> Optional[Dict]:
        """Get upcoming movies."""
        return self._request('GET', 'discover/movies/upcoming', params={'page': page})

    # =========================
    # USER MANAGEMENT
    # =========================

    def get_users(self, take: int = 20, skip: int = 0) -> Optional[Dict]:
        """Get all users."""
        params = {'take': take, 'skip': skip}
        return self._request('GET', 'user', params=params)

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get specific user."""
        return self._request('GET', f'user/{user_id}')

    def get_current_user(self) -> Optional[Dict]:
        """Get current user info."""
        return self._request('GET', 'auth/me')

    def get_user_requests(self, user_id: int, take: int = 20) -> Optional[Dict]:
        """Get requests by user."""
        params = {'take': take}
        return self._request('GET', f'user/{user_id}/requests', params=params)

    # =========================
    # SETTINGS & STATUS
    # =========================

    def get_status(self) -> Optional[Dict]:
        """Get Overseerr status."""
        return self._request('GET', 'status')

    def get_settings(self) -> Optional[Dict]:
        """Get Overseerr settings."""
        return self._request('GET', 'settings/main')

    def get_radarr_settings(self) -> List[Dict]:
        """Get Radarr server configurations."""
        result = self._request('GET', 'settings/radarr')
        return result if result else []

    def get_sonarr_settings(self) -> List[Dict]:
        """Get Sonarr server configurations."""
        result = self._request('GET', 'settings/sonarr')
        return result if result else []

    # =========================
    # ISSUES
    # =========================

    def get_issues(self, take: int = 20, skip: int = 0) -> Optional[Dict]:
        """Get reported issues."""
        params = {'take': take, 'skip': skip}
        return self._request('GET', 'issue', params=params)

    def get_issue(self, issue_id: int) -> Optional[Dict]:
        """Get specific issue."""
        return self._request('GET', f'issue/{issue_id}')

    def create_issue(self, media_type: str, media_id: int,
                    issue_type: str, message: str) -> Optional[Dict]:
        """Report an issue."""
        data = {
            'mediaType': media_type,
            'mediaId': media_id,
            'issueType': issue_type,
            'message': message
        }
        return self._request('POST', 'issue', json=data)


class ProwlarrAPI(ServiceAPI):
    """Prowlarr API Client for indexer management."""

    def __init__(self, service: Service):
        super().__init__(service)
        self.headers = {"X-Api-Key": self.api_key}

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        url = f"{self.base_url}/api/v1/{endpoint.lstrip('/')}"
        kwargs['headers'] = self.headers
        kwargs.setdefault('timeout', 10)
        try:
            response = requests.request(method, url, **kwargs)
            if response.ok:
                return response.json() if response.content else {}
            return None
        except requests.RequestException:
            return None

    def test_connection(self) -> bool:
        try:
            url = f"{self.base_url}/api/v1/system/status"
            response = requests.get(url, headers=self.headers, timeout=5)
            is_online = response.ok
        except requests.RequestException:
            is_online = False
        self.service.is_online = is_online
        self.service.last_checked = timezone.now()
        self.service.save()
        return is_online

    def fetch_stats(self) -> dict:
        stats = {
            'is_online': self.test_connection(),
            'version': None,
            'total_indexers': 0,
            'enabled_indexers': 0,
            'total_queries': 0,
            'total_grabs': 0,
            'total_failed': 0,
            'health_issues': [],
            'indexer_stats': [],
        }

        if not stats['is_online']:
            return stats

        try:
            status = self._request('GET', 'system/status')
            if status:
                stats['version'] = status.get('version')

            indexers = self._request('GET', 'indexer')
            if indexers:
                stats['total_indexers'] = len(indexers)
                stats['enabled_indexers'] = sum(1 for i in indexers if i.get('enable'))
                indexer_name_map = {i['id']: i['name'] for i in indexers}
            else:
                indexer_name_map = {}

            indexer_stats = self._request('GET', 'indexerstats')
            if indexer_stats and 'indexers' in indexer_stats:
                for entry in indexer_stats['indexers']:
                    stats['total_queries'] += entry.get('numberOfQueries', 0)
                    stats['total_grabs'] += entry.get('numberOfGrabs', 0)
                    stats['total_failed'] += entry.get('numberOfFailedQueries', 0)
                    stats['indexer_stats'].append({
                        'name': entry.get('indexerName', indexer_name_map.get(entry.get('indexerId'), 'Unknown')),
                        'queries': entry.get('numberOfQueries', 0),
                        'grabs': entry.get('numberOfGrabs', 0),
                        'failed': entry.get('numberOfFailedQueries', 0),
                        'avg_response_ms': entry.get('averageResponseTime', 0),
                    })
                stats['indexer_stats'].sort(key=lambda x: x['queries'], reverse=True)

            health = self._request('GET', 'health')
            if health:
                stats['health_issues'] = [
                    {'type': h.get('type', 'warning'), 'message': h.get('message', '')}
                    for h in health
                ]

        except Exception:
            pass

        return stats


class JDownloaderAPI(ServiceAPI):
    """JDownloader MyJDownloader Cloud API Client.

    Service configuration:
      url      → https://my.jdownloader.org  (or any placeholder URL)
      username → MyJDownloader account email
      password → MyJDownloader account password
      api_key  → Device name to connect to (leave blank to use first device)
    """

    def _get_device(self):
        """Authenticate and return the target JDownloader device."""
        if not MYJDAPI_AVAILABLE:
            return None
        jd = _myjdapi.Myjdapi()
        jd.set_app_key("HomeDashboard")
        jd.connect(self.service.username, self.service.password)
        jd.update_devices()
        device_name = self.api_key  # api_key stores the device name
        if device_name:
            return jd.get_device(device_name)
        devices = jd.list_devices()
        if devices:
            return jd.get_device(devices[0]['name'])
        return None

    def test_connection(self) -> bool:
        try:
            device = self._get_device()
            is_online = device is not None
        except Exception:
            is_online = False
        self.service.is_online = is_online
        self.service.last_checked = timezone.now()
        self.service.save()
        return is_online

    def fetch_stats(self) -> dict:
        stats = {
            'is_online': False,
            'device_name': '',
            'state': 'UNKNOWN',
            'speed_bytes': 0,
            'total_packages': 0,
            'active_downloads': 0,
            'finished_packages': 0,
            'total_bytes': 0,
            'loaded_bytes': 0,
            'packages': [],
        }

        if not MYJDAPI_AVAILABLE:
            return stats

        try:
            device = self._get_device()
            if not device:
                self.service.is_online = False
                self.service.last_checked = timezone.now()
                self.service.save()
                return stats

            stats['is_online'] = True
            stats['device_name'] = device.name
            self.service.is_online = True
            self.service.last_checked = timezone.now()
            self.service.save()

            state = device.downloadcontroller.get_current_state()
            stats['state'] = state if state else 'UNKNOWN'

            speed = device.downloadcontroller.get_speed_in_bytes()
            stats['speed_bytes'] = speed if speed else 0

            packages = device.downloads.query_packages([{
                "bytesLoaded": True,
                "bytesTotal": True,
                "childCount": True,
                "enabled": True,
                "eta": True,
                "finished": True,
                "running": True,
                "speed": True,
                "status": True,
                "maxResults": 20,
                "startAt": 0,
            }])

            if packages:
                stats['total_packages'] = len(packages)
                stats['active_downloads'] = sum(1 for p in packages if p.get('running'))
                stats['finished_packages'] = sum(1 for p in packages if p.get('finished'))
                stats['total_bytes'] = sum(p.get('bytesTotal') or 0 for p in packages)
                stats['loaded_bytes'] = sum(p.get('bytesLoaded') or 0 for p in packages)
                stats['packages'] = packages[:10]

        except Exception:
            pass

        return stats


class QBittorrentAPI(ServiceAPI):
    """qBittorrent WebUI API v2 client.

    Service configuration:
      url      → http://192.168.x.x:8080
      username → WebUI username  (default: admin)
      password → WebUI password
    """

    def _session(self) -> Optional[requests.Session]:
        """Authenticate and return a logged-in requests Session."""
        sess = requests.Session()
        try:
            resp = sess.post(
                f"{self.base_url}/api/v2/auth/login",
                data={'username': self.service.username or 'admin',
                      'password': self.service.password},
                timeout=5,
            )
            if resp.ok and resp.text.strip() == 'Ok.':
                return sess
        except requests.RequestException:
            pass
        return None

    def _get(self, sess: requests.Session, path: str, **params) -> Optional[Any]:
        try:
            r = sess.get(f"{self.base_url}{path}", params=params, timeout=10)
            if r.ok:
                ct = r.headers.get('content-type', '')
                return r.json() if 'json' in ct else r.text.strip()
        except requests.RequestException:
            pass
        return None

    def test_connection(self) -> bool:
        try:
            sess = self._session()
            is_online = sess is not None
        except Exception:
            is_online = False
        self.service.is_online = is_online
        self.service.last_checked = timezone.now()
        self.service.save()
        return is_online

    @staticmethod
    def _fmt_eta(eta: int) -> str:
        if eta < 0 or eta >= 8640000:
            return '∞'
        if eta >= 3600:
            return f"{eta // 3600}h {(eta % 3600) // 60}m"
        if eta >= 60:
            return f"{eta // 60}m {eta % 60}s"
        return f"{eta}s"

    def fetch_stats(self) -> dict:
        stats = {
            'is_online': False,
            'version': None,
            'dl_speed': 0,
            'up_speed': 0,
            'dl_data': 0,
            'up_data': 0,
            'connection_status': 'disconnected',
            'dht_nodes': 0,
            'total_torrents': 0,
            'active_torrents': 0,
            'downloading': 0,
            'seeding': 0,
            'paused': 0,
            'errored': 0,
            'torrents': [],
        }

        sess = self._session()
        if not sess:
            self.service.is_online = False
            self.service.last_checked = timezone.now()
            self.service.save()
            return stats

        self.service.is_online = True
        self.service.last_checked = timezone.now()
        self.service.save()
        stats['is_online'] = True

        try:
            version = self._get(sess, '/api/v2/app/version')
            if version:
                stats['version'] = version

            transfer = self._get(sess, '/api/v2/transfer/info')
            if transfer:
                stats['dl_speed'] = transfer.get('dl_info_speed', 0)
                stats['up_speed'] = transfer.get('up_info_speed', 0)
                stats['dl_data'] = transfer.get('dl_info_data', 0)
                stats['up_data'] = transfer.get('up_info_data', 0)
                stats['connection_status'] = transfer.get('connection_status', 'disconnected')
                stats['dht_nodes'] = transfer.get('dht_nodes', 0)

            torrents = self._get(sess, '/api/v2/torrents/info',
                                 sort='added_on', reverse=True, limit=100) or []
            stats['total_torrents'] = len(torrents)

            for t in torrents:
                state = t.get('state', 'unknown')
                label, colour = QB_STATE_MAP.get(state, ('Unknown', 'text-muted-foreground'))
                t['state_label'] = label
                t['state_colour'] = colour
                t['display_eta'] = self._fmt_eta(t.get('eta', -1))
                pct = t.get('progress', 0)
                t['progress_pct'] = round(pct * 100, 1)
                if state in ('downloading', 'stalledDL', 'metaDL', 'forcedDL', 'checkingDL', 'queuedDL', 'allocating'):
                    stats['downloading'] += 1
                    stats['active_torrents'] += 1
                elif state in ('uploading', 'stalledUP', 'forcedUP', 'queuedUP', 'checkingUP'):
                    stats['seeding'] += 1
                    stats['active_torrents'] += 1
                elif state in ('pausedDL', 'pausedUP'):
                    stats['paused'] += 1
                elif state in ('error', 'missingFiles'):
                    stats['errored'] += 1

            stats['torrents'] = torrents

        except Exception:
            pass

        return stats

    def fetch_live(self) -> dict:
        """Lightweight live fetch — returns only what the GUI table needs."""
        result = {'is_online': False, 'dl_speed': 0, 'up_speed': 0,
                  'connection_status': 'disconnected', 'torrents': []}
        sess = self._session()
        if not sess:
            return result
        result['is_online'] = True
        try:
            transfer = self._get(sess, '/api/v2/transfer/info') or {}
            result['dl_speed'] = transfer.get('dl_info_speed', 0)
            result['up_speed'] = transfer.get('up_info_speed', 0)
            result['connection_status'] = transfer.get('connection_status', 'disconnected')

            torrents = self._get(sess, '/api/v2/torrents/info',
                                 sort='added_on', reverse=True) or []
            for t in torrents:
                state = t.get('state', 'unknown')
                label, colour = QB_STATE_MAP.get(state, ('Unknown', 'text-muted-foreground'))
                t['state_label'] = label
                t['state_colour'] = colour
                t['display_eta'] = self._fmt_eta(t.get('eta', -1))
                t['progress_pct'] = round(t.get('progress', 0) * 100, 1)
            result['torrents'] = torrents
        except Exception:
            pass
        return result


class PlexAPI(ServiceAPI):
    """
    Plex Media Server API.
    url     = http://host:32400
    api_key = X-Plex-Token
    """

    _HEADERS = {'Accept': 'application/json', 'X-Plex-Client-Identifier': 'HomeDashboard'}

    def _get(self, endpoint: str, **params) -> Optional[Dict]:
        params['X-Plex-Token'] = self.api_key
        try:
            resp = requests.get(
                f"{self.base_url}{endpoint}",
                params=params,
                headers=self._HEADERS,
                timeout=10,
            )
            return resp.json() if resp.ok else None
        except requests.RequestException:
            return None

    def test_connection(self) -> bool:
        data = self._get('/identity')
        is_online = data is not None
        self.service.is_online = is_online
        self.service.last_checked = timezone.now()
        self.service.save()
        return is_online

    def fetch_stats(self) -> dict:
        stats = {
            'is_online': False,
            'version': None,
            'server_name': None,
            'active_streams': 0,
            'total_movies': 0,
            'total_shows': 0,
            'total_music': 0,
            'libraries': [],
            'sessions': [],
        }

        identity = self._get('/identity')
        if not identity:
            self.service.is_online = False
            self.service.last_checked = timezone.now()
            self.service.save()
            return stats

        self.service.is_online = True
        self.service.last_checked = timezone.now()
        self.service.save()
        stats['is_online'] = True

        mc = identity.get('MediaContainer', {})
        stats['version'] = mc.get('version')

        # friendlyName lives in the root / endpoint, not /identity
        root_data = self._get('/')
        if root_data:
            stats['server_name'] = root_data.get('MediaContainer', {}).get('friendlyName')

        try:
            sessions_data = self._get('/status/sessions')
            if sessions_data:
                smc = sessions_data.get('MediaContainer', {})
                sessions = smc.get('Metadata', []) or []
                stats['active_streams'] = smc.get('size', len(sessions))
                # Annotate each session with a friendly state label
                for s in sessions:
                    player = s.get('Player', {})
                    s['player_title'] = player.get('title', 'Unknown')
                    s['player_state'] = player.get('state', 'playing').capitalize()
                    s['media_type'] = s.get('type', 'unknown')
                    s['grandparent_title'] = s.get('grandparentTitle', '')
                    duration = s.get('duration', 0) or 0
                    view_offset = s.get('viewOffset', 0) or 0
                    s['progress_pct'] = round(view_offset / duration * 100, 1) if duration else 0
                    user = s.get('User', {})
                    s['user_title'] = user.get('title', 'Unknown')
                stats['sessions'] = sessions[:10]

            sections_data = self._get('/library/sections')
            if sections_data:
                dirs = sections_data.get('MediaContainer', {}).get('Directory', []) or []
                libs = []
                for sec in dirs:
                    lib_type = sec.get('type', '')
                    key = sec.get('key')
                    # Fetch item count efficiently via container-size=0
                    count = 0
                    count_data = self._get(
                        f'/library/sections/{key}/all',
                        **{'X-Plex-Container-Start': 0, 'X-Plex-Container-Size': 0}
                    )
                    if count_data:
                        count = count_data.get('MediaContainer', {}).get('totalSize', 0)
                    libs.append({
                        'key': key,
                        'title': sec.get('title', ''),
                        'type': lib_type,
                        'count': count,
                    })
                    if lib_type == 'movie':
                        stats['total_movies'] += count
                    elif lib_type == 'show':
                        stats['total_shows'] += count
                    elif lib_type == 'artist':
                        stats['total_music'] += count
                stats['libraries'] = libs
        except Exception:
            pass

        return stats


class TautulliAPI(ServiceAPI):
    """
    Tautulli API.
    url     = http://host:8181
    api_key = API key from Tautulli Settings > Web Interface
    """

    def _cmd(self, cmd: str, **params) -> Optional[Any]:
        params.update({'apikey': self.api_key, 'cmd': cmd})
        try:
            resp = requests.get(f"{self.base_url}/api/v2", params=params, timeout=10)
            if resp.ok:
                data = resp.json()
                if data.get('response', {}).get('result') == 'success':
                    return data['response'].get('data')
            return None
        except requests.RequestException:
            return None

    def test_connection(self) -> bool:
        data = self._cmd('get_server_info')
        is_online = data is not None
        self.service.is_online = is_online
        self.service.last_checked = timezone.now()
        self.service.save()
        return is_online

    def fetch_stats(self) -> dict:
        stats = {
            'is_online': False,
            'version': None,
            'server_name': None,
            'active_streams': 0,
            'stream_count_direct_play': 0,
            'stream_count_direct_stream': 0,
            'stream_count_transcode': 0,
            'sessions': [],
            'recently_added': [],
            'top_movies': [],
            'top_shows': [],
        }

        server_info = self._cmd('get_server_info')
        if not server_info:
            self.service.is_online = False
            self.service.last_checked = timezone.now()
            self.service.save()
            return stats

        self.service.is_online = True
        self.service.last_checked = timezone.now()
        self.service.save()
        stats['is_online'] = True
        stats['server_name'] = server_info.get('pms_name')
        stats['version'] = server_info.get('pms_version')

        try:
            activity = self._cmd('get_activity')
            if activity:
                stats['active_streams'] = activity.get('stream_count', 0)
                stats['stream_count_direct_play'] = activity.get('stream_count_direct_play', 0)
                stats['stream_count_direct_stream'] = activity.get('stream_count_direct_stream', 0)
                stats['stream_count_transcode'] = activity.get('stream_count_transcode', 0)
                sessions = activity.get('sessions', []) or []
                for s in sessions:
                    s['progress_pct'] = s.get('progress_percent', 0)
                stats['sessions'] = sessions[:10]

            recently = self._cmd('get_recently_added', count=10)
            if recently:
                stats['recently_added'] = (recently.get('recently_added', []) or [])[:10]

            home_stats = self._cmd('get_home_stats', time_range=7, stats_count=5)
            if home_stats and isinstance(home_stats, list):
                for stat in home_stats:
                    sid = stat.get('stat_id', '')
                    if sid == 'top_movies':
                        stats['top_movies'] = stat.get('rows', [])[:5]
                    elif sid == 'top_tv':
                        stats['top_shows'] = stat.get('rows', [])[:5]
        except Exception:
            pass

        return stats


class BazarrAPI(ServiceAPI):
    """
    Bazarr subtitle manager API.
    url     = http://host:6767
    api_key = API key from Bazarr Settings > General
    """

    def _request(self, endpoint: str, **params) -> Optional[Dict]:
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        try:
            resp = requests.get(
                url, params=params,
                headers={'X-API-KEY': self.api_key, 'Accept': 'application/json'},
                timeout=10,
            )
            return resp.json() if resp.ok else None
        except requests.RequestException:
            return None

    def test_connection(self) -> bool:
        data = self._request('system/status')
        is_online = data is not None
        self.service.is_online = is_online
        self.service.last_checked = timezone.now()
        self.service.save()
        return is_online

    def fetch_stats(self) -> dict:
        stats = {
            'is_online': False,
            'version': None,
            'episodes_missing': 0,
            'movies_missing': 0,
            'total_providers': 0,
            'enabled_providers': 0,
            'subtitles_today': 0,
            'subtitles_week': 0,
            'subtitles_month': 0,
            'wanted_episodes': [],
            'wanted_movies': [],
            'providers': [],
        }

        status = self._request('system/status')
        if not status:
            self.service.is_online = False
            self.service.last_checked = timezone.now()
            self.service.save()
            return stats

        self.service.is_online = True
        self.service.last_checked = timezone.now()
        self.service.save()
        stats['is_online'] = True

        sdata = status.get('data', status)  # some versions wrap in 'data'
        stats['version'] = sdata.get('bazarr_version')

        try:
            # Badge counts (missing subtitles)
            badges = self._request('badges')
            if badges:
                stats['episodes_missing'] = badges.get('episodes', 0)
                stats['movies_missing'] = badges.get('movies', 0)

            # History stats
            history = self._request('history/stats')
            if history:
                hdata = history.get('data', history)
                stats['subtitles_today'] = hdata.get('today', 0)
                stats['subtitles_week'] = hdata.get('week', 0)
                stats['subtitles_month'] = hdata.get('month', 0)

            # Wanted episodes (missing)
            wanted_eps = self._request('wanted/episodes', start=0, length=10)
            if wanted_eps:
                stats['wanted_episodes'] = (wanted_eps.get('data', []) or [])[:10]

            # Wanted movies (missing)
            wanted_mov = self._request('wanted/movies', start=0, length=10)
            if wanted_mov:
                stats['wanted_movies'] = (wanted_mov.get('data', []) or [])[:10]

            # Providers
            providers = self._request('providers')
            if providers:
                prov_list = providers.get('data', []) or []
                stats['providers'] = prov_list
                stats['total_providers'] = len(prov_list)
                stats['enabled_providers'] = sum(
                    1 for p in prov_list if p.get('enabled', True)
                )
        except Exception:
            pass

        return stats


class ProxmoxAPI(ServiceAPI):
    """
    Proxmox VE API.
    url      = https://host:8006
    api_key  = API Token ID  (e.g. root@pam!mytoken)
    password = API Token Secret (UUID)
    """

    def _get(self, endpoint: str, **params) -> Optional[Dict]:
        url = f"{self.base_url}/api2/json/{endpoint.lstrip('/')}"
        token_id = self.api_key
        token_secret = self.service.password
        headers = {'Authorization': f'PVEAPIToken={token_id}={token_secret}'}
        try:
            resp = requests.get(url, params=params, headers=headers,
                                timeout=10, verify=False)
            if resp.ok:
                return resp.json()
            return None
        except requests.RequestException:
            return None

    def test_connection(self) -> bool:
        data = self._get('version')
        is_online = data is not None
        self.service.is_online = is_online
        self.service.last_checked = timezone.now()
        self.service.save()
        return is_online

    @staticmethod
    def _pct(used, total) -> float:
        return round(used / total * 100, 1) if total else 0.0

    def fetch_stats(self) -> dict:
        stats = {
            'is_online': False,
            'version': None,
            'total_nodes': 0,
            'online_nodes': 0,
            'total_vms': 0,
            'running_vms': 0,
            'stopped_vms': 0,
            'total_containers': 0,
            'running_containers': 0,
            'stopped_containers': 0,
            'cluster_cpu_pct': 0.0,
            'cluster_mem_used': 0,
            'cluster_mem_total': 0,
            'cluster_disk_used': 0,
            'cluster_disk_total': 0,
            'nodes': [],
            'vms': [],
            'containers': [],
        }

        ver = self._get('version')
        if not ver:
            self.service.is_online = False
            self.service.last_checked = timezone.now()
            self.service.save()
            return stats

        self.service.is_online = True
        self.service.last_checked = timezone.now()
        self.service.save()
        stats['is_online'] = True
        stats['version'] = ver.get('data', {}).get('version')

        try:
            resources = self._get('cluster/resources')
            if not resources:
                return stats

            items = resources.get('data', []) or []
            nodes, vms, containers = [], [], []

            for item in items:
                rtype = item.get('type')
                if rtype == 'node':
                    cpu_pct = round(item.get('cpu', 0) * 100, 1)
                    mem_used = item.get('mem', 0)
                    mem_total = item.get('maxmem', 0)
                    disk_used = item.get('disk', 0)
                    disk_total = item.get('maxdisk', 0)
                    nodes.append({
                        'name': item.get('node'),
                        'status': item.get('status', 'unknown'),
                        'cpu_pct': cpu_pct,
                        'mem_used': mem_used,
                        'mem_total': mem_total,
                        'mem_pct': self._pct(mem_used, mem_total),
                        'disk_used': disk_used,
                        'disk_total': disk_total,
                        'disk_pct': self._pct(disk_used, disk_total),
                        'uptime': item.get('uptime', 0),
                    })
                    stats['cluster_mem_used'] += mem_used
                    stats['cluster_mem_total'] += mem_total
                    stats['cluster_disk_used'] += disk_used
                    stats['cluster_disk_total'] += disk_total

                elif rtype == 'qemu':
                    status = item.get('status', 'stopped')
                    cpu_pct = round(item.get('cpu', 0) * 100, 1)
                    vms.append({
                        'vmid': item.get('vmid'),
                        'name': item.get('name', f"VM {item.get('vmid')}"),
                        'node': item.get('node'),
                        'status': status,
                        'cpu_pct': cpu_pct,
                        'mem_used': item.get('mem', 0),
                        'mem_total': item.get('maxmem', 0),
                        'disk': item.get('disk', 0),
                        'uptime': item.get('uptime', 0),
                    })
                    stats['total_vms'] += 1
                    if status == 'running':
                        stats['running_vms'] += 1
                    else:
                        stats['stopped_vms'] += 1

                elif rtype == 'lxc':
                    status = item.get('status', 'stopped')
                    cpu_pct = round(item.get('cpu', 0) * 100, 1)
                    containers.append({
                        'vmid': item.get('vmid'),
                        'name': item.get('name', f"CT {item.get('vmid')}"),
                        'node': item.get('node'),
                        'status': status,
                        'cpu_pct': cpu_pct,
                        'mem_used': item.get('mem', 0),
                        'mem_total': item.get('maxmem', 0),
                        'disk': item.get('disk', 0),
                        'uptime': item.get('uptime', 0),
                    })
                    stats['total_containers'] += 1
                    if status == 'running':
                        stats['running_containers'] += 1
                    else:
                        stats['stopped_containers'] += 1

            stats['nodes'] = nodes
            stats['vms'] = sorted(vms, key=lambda x: x['name'])
            stats['containers'] = sorted(containers, key=lambda x: x['name'])
            stats['total_nodes'] = len(nodes)
            stats['online_nodes'] = sum(1 for n in nodes if n['status'] == 'online')

            # Cluster-wide average CPU
            cpu_vals = [item.get('cpu', 0) for item in items if item.get('type') == 'node']
            if cpu_vals:
                stats['cluster_cpu_pct'] = round(sum(cpu_vals) / len(cpu_vals) * 100, 1)

        except Exception:
            pass

        return stats

    def fetch_live(self) -> dict:
        """Lightweight live fetch — returns vms and containers with mem_pct."""
        result = {'is_online': False, 'vms': [], 'containers': []}
        resources = self._get('cluster/resources')
        if not resources:
            return result
        result['is_online'] = True
        for item in (resources.get('data') or []):
            rtype = item.get('type')
            if rtype not in ('qemu', 'lxc'):
                continue
            mem_used = item.get('mem', 0)
            mem_total = item.get('maxmem', 0)
            entry = {
                'vmid': item.get('vmid'),
                'name': item.get('name', f"{'VM' if rtype == 'qemu' else 'CT'} {item.get('vmid')}"),
                'node': item.get('node'),
                'status': item.get('status', 'stopped'),
                'cpu_pct': round(item.get('cpu', 0) * 100, 1),
                'mem_used': mem_used,
                'mem_total': mem_total,
                'mem_pct': self._pct(mem_used, mem_total),
            }
            if rtype == 'qemu':
                result['vms'].append(entry)
            else:
                result['containers'].append(entry)
        result['vms'] = sorted(result['vms'], key=lambda x: x['name'])
        result['containers'] = sorted(result['containers'], key=lambda x: x['name'])
        return result
