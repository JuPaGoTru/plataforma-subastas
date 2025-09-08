from django.http import HttpResponseForbidden
from .models import BannedIP

class IPBanMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = request.META.get('REMOTE_ADDR')
        # Si usas ngrok, prueba también con 'X-Forwarded-For'
        forwarded_ip = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded_ip:
            # Puede venir como lista (algunas configuraciones), entonces toma el primero
            if isinstance(forwarded_ip, list):
                ip_to_check = forwarded_ip[0]
            else:
                ip_to_check = forwarded_ip.split(',')[0].strip()
        else:
            ip_to_check = ip


        if BannedIP.objects.filter(ip_address=ip_to_check).exists():
            return HttpResponseForbidden("Acceso bloqueado (IP baneada)")
        return self.get_response(request)

class DisableAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.public_paths = [
            '/',  # Página principal
            '/product/',  # Todas las URLs de productos
            '/api/product/',  # APIs de productos
            '/join/',  # Página de unirse
        ]

    def __call__(self, request):
        # Verificar si la path es pública
        if any(request.path.startswith(path) for path in self.public_paths):
            # Desactivar completamente la autenticación para estas paths
            request.user = None
            # Crear sesión si no existe
            if not request.session.session_key:
                request.session.create()
        
        response = self.get_response(request)
        return response