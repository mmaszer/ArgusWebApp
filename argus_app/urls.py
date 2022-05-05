from django.urls import path, include
from argus_app import views

urlpatterns = [
    path("", views.home, name="home"),
    path("argus_app", views.run, name="run"),
    path("argus_app", views.read_file, name="read_file"),
    path("accounts/", include("accounts.urls")), 
    path("accounts/", include("django.contrib.auth.urls")),
]