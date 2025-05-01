from django.urls import path
from . import views
from .views import login_view, logout_view, register_view, profile_view, update_avatar, update_username
urlpatterns = [
    path("", views.home, name="home"),
    path("enterprises/", views.enterprise_list, name="enterprise_list"),
    path("indicators/", views.indicator_list, name="indicator_list"),
    path("indicator-values/", views.indicator_values, name="indicator_values"),
    path("indicator-values/add/", views.indicator_add, name="indicator_add"),
    path("currencies/", views.currency_list, name="currency_list"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("register/", register_view, name="register"),
    path("enterprises/add/", views.enterprise_add, name="enterprise_add"),
    path('profile/', profile_view, name='profile'),
    path("profile/update-avatar/", update_avatar, name="update_avatar"),
    path("profile/update-username/", update_username, name="update_username"),
]
