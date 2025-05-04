from .models import Users

def avatar_url(request):
    if request.user.is_authenticated:
        try:
            user = Users.objects.get(username=request.user.username)
            return {'avatar_url': user.avatar_url}
        except Users.DoesNotExist:
            return {'avatar_url': None}
    return {'avatar_url': None}
