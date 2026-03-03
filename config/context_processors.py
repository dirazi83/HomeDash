from services.models import Service

def global_services(request):
    """
    Context processor to inject all active services into every template,
    primarily for rendering the dynamic sidebar navigation.
    """
    return {
        'global_services': Service.objects.filter(is_active=True).order_by('name')
    }
