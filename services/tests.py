from django.test import TestCase
from django.urls import reverse
from .models import Service, ServiceType


class ServiceViewsTest(TestCase):
    def test_service_list_excludes_inactive(self):
        Service.objects.create(name="Active", service_type=ServiceType.PFSENSE, url="http://x", is_active=True)
        Service.objects.create(name="Inactive", service_type=ServiceType.PFSENSE, url="http://y", is_active=False)
        resp = self.client.get(reverse('service_list'))
        self.assertContains(resp, "Active")
        self.assertNotContains(resp, "Inactive")

    def test_service_delete_marks_inactive_and_removes(self):
        svc = Service.objects.create(name="ToBeGone", service_type=ServiceType.PFSENSE, url="http://z", is_active=True)
        # perform delete via POST (non-HTMX path)
        resp = self.client.post(reverse('service_delete', args=[svc.pk]))
        # should redirect back to list
        self.assertEqual(resp.status_code, 302)
        # fetch from DB
        with self.assertRaises(Service.DoesNotExist):
            Service.objects.get(pk=svc.pk)
        # simulate case where delete failed by re-creating
        svc2 = Service.objects.create(name="Later", service_type=ServiceType.PFSENSE, url="http://z", is_active=True)
        # monkey-patch delete to raise
        original_delete = Service.delete
        def bad_delete(self, *args, **kwargs):
            raise Exception("oops")
        Service.delete = bad_delete
        resp2 = self.client.post(reverse('service_delete', args=[svc2.pk]))
        self.assertEqual(resp2.status_code, 302)
        # service should still exist but be inactive
        svc2.refresh_from_db()
        self.assertFalse(svc2.is_active)
        # restore delete
        Service.delete = original_delete
