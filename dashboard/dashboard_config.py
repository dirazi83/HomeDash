"""
Dashboard customization configuration module.

This module provides configuration options for customizing the dashboard
appearance and behavior for different service types.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class WidgetConfig:
    """Configuration for dashboard widget display."""
    show_version: bool = True
    show_queue_size: bool = True
    show_missing_count: bool = True
    refresh_interval: int = 10  # seconds
    height: str = "h-48"  # Tailwind CSS class


@dataclass
class DashboardTabConfig:
    """Configuration for dashboard tabs."""
    enabled: bool = True
    label: str = ""
    icon: Optional[str] = None
    default_active: bool = False


class RadarrDashboardConfig:
    """
    Configuration options for Radarr dashboard customization.

    Usage:
        config = RadarrDashboardConfig()
        config.widget.show_missing_count = False
        config.tabs['movies'].enabled = True
    """

    def __init__(self):
        # Widget configuration
        self.widget = WidgetConfig(
            show_version=True,
            show_queue_size=True,
            show_missing_count=True,
            refresh_interval=10,
            height="h-48"
        )

        # Tab configuration
        self.tabs: Dict[str, DashboardTabConfig] = {
            'movies': DashboardTabConfig(
                enabled=True,
                label='Movies',
                default_active=True
            ),
            'queue': DashboardTabConfig(
                enabled=True,
                label='Queue'
            ),
            'calendar': DashboardTabConfig(
                enabled=True,
                label='Calendar'
            ),
            'history': DashboardTabConfig(
                enabled=True,
                label='History'
            ),
            'system': DashboardTabConfig(
                enabled=True,
                label='System'
            ),
        }

        # Stats display configuration
        self.stats_display = {
            'show_total_movies': True,
            'show_downloaded_movies': True,
            'show_monitored_movies': True,
            'show_missing_movies': True,
            'show_queue_size': True,
            'show_disk_space': True,
            'show_upcoming_movies': True,
        }

        # Feature flags
        self.features = {
            'enable_movie_add': True,
            'enable_movie_delete': True,
            'enable_movie_edit': True,
            'enable_queue_management': True,
            'enable_search': True,
            'enable_calendar': True,
            'enable_history': True,
        }

        # Display preferences
        self.display = {
            'movies_per_page': 20,
            'queue_items_per_page': 20,
            'history_items_per_page': 20,
            'default_sort': 'title',
            'show_posters': False,  # Future feature
            'compact_view': False,
        }

    def get_enabled_tabs(self) -> List[str]:
        """Get list of enabled tab names."""
        return [name for name, config in self.tabs.items() if config.enabled]

    def get_default_tab(self) -> Optional[str]:
        """Get the default active tab name."""
        for name, config in self.tabs.items():
            if config.default_active and config.enabled:
                return name
        # Return first enabled tab if no default set
        enabled = self.get_enabled_tabs()
        return enabled[0] if enabled else None

    def to_context(self) -> Dict:
        """Convert configuration to template context dictionary."""
        return {
            'widget_config': {
                'show_version': self.widget.show_version,
                'show_queue_size': self.widget.show_queue_size,
                'show_missing_count': self.widget.show_missing_count,
                'refresh_interval': self.widget.refresh_interval,
                'height': self.widget.height,
            },
            'enabled_tabs': self.get_enabled_tabs(),
            'default_tab': self.get_default_tab(),
            'stats_display': self.stats_display,
            'features': self.features,
            'display': self.display,
        }


# Global configuration instances
RADARR_CONFIG = RadarrDashboardConfig()


def get_dashboard_config(service_type: str) -> Dict:
    """
    Get dashboard configuration for a specific service type.

    Args:
        service_type: The type of service (e.g., 'radarr', 'sonarr')

    Returns:
        Configuration dictionary for the service type
    """
    if service_type == 'radarr':
        return RADARR_CONFIG.to_context()

    # Return minimal config for other service types
    return {
        'widget_config': {
            'refresh_interval': 10,
            'height': 'h-48'
        },
        'enabled_tabs': [],
        'default_tab': None,
        'stats_display': {},
        'features': {},
        'display': {},
    }
