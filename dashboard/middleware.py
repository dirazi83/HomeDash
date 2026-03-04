from django.shortcuts import redirect

_EXEMPT = ('/setup/', '/login/', '/logout/', '/admin/', '/static/')


def _is_exempt(path):
    return any(path.startswith(p) for p in _EXEMPT)


class SetupMiddleware:
    """Redirect every request to the setup wizard until a superuser exists."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if _is_exempt(request.path):
            return self.get_response(request)
        try:
            from django.contrib.auth.models import User
            if not User.objects.filter(is_superuser=True).exists():
                return redirect('/setup/')
        except Exception:
            # DB not ready yet (e.g. during migrations)
            pass
        return self.get_response(request)


class LoginRequiredMiddleware:
    """Redirect unauthenticated users to the login page."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if _is_exempt(request.path):
            return self.get_response(request)
        if not request.user.is_authenticated:
            return redirect(f'/login/?next={request.path}')
        return self.get_response(request)
