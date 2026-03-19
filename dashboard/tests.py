from django.test import TestCase
from django.urls import reverse
from services.models import Service, ServiceType


class WidgetUpdateTests(TestCase):
    def setUp(self):
        # simple service entry that will not actually be reached over network
        self.svc = Service.objects.create(
            name="pfSense Test",
            service_type=ServiceType.PFSENSE,
            url="https://example.local",
        )

    def test_widget_updates_and_disappears_after_delete(self):
        # initial widget request should return some HTML (even if empty stats)
        url = reverse('widget_update', args=[self.svc.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.content.strip() != b"", "widget response should contain markup")

        # delete the service (simulate HTMX request)
        delete_url = reverse('service_delete', args=[self.svc.pk])
        resp2 = self.client.post(delete_url, HTTP_HX_REQUEST='true')
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2['HX-Trigger'], 'serviceDeleted')

        # after deletion, the widget endpoint should return empty body
        resp3 = self.client.get(url)
        self.assertEqual(resp3.status_code, 200)
        self.assertEqual(resp3.content, b"")

    def test_get_stats_returns_cached_value(self):
        # manually populate cache and ensure helper returns it
        from django.core.cache import cache as _cache
        cache_key = f"service_stats_{self.svc.pk}"
        _cache.set(cache_key, {'fake': 'data'}, timeout=30)
        # calling widget_update should now include our fake data
        url = reverse('widget_update', args=[self.svc.pk])
        resp = self.client.get(url)
        self.assertIn(b'fake', resp.content)
