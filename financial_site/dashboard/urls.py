from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("enterprises/", views.enterprise_list, name="enterprise_list"),
    path("indicators/", views.indicator_list, name="indicator_list"),
    path("indicator-values/", views.indicator_values, name="indicator_values"),
    path("indicator-values/add/", views.indicator_add, name="indicator_add"),
    path("currencies/", views.currency_list, name="currency_list"),
]
