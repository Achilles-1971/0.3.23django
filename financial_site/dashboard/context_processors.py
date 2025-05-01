from .models import Users

def avatar_url(request):
    return {'avatar_url': request.session.get('avatar_url')}
