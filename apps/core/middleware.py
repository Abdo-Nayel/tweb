class ActivityLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.method == 'POST' and getattr(request, 'user', None) and request.user.is_authenticated:
            if request.path not in ('/', '/login/', '/logout/'):
                from apps.core.activity import log_from_request
                try:
                    log_from_request(request)
                except Exception:
                    pass
        return response
