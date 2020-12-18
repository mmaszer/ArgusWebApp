from django.urls import path
from argus_app import views

urlpatterns = [
    path("", views.home, name="home"),
    #path("", views.simple_upload, name="simple_upload"),
    path("argus_app", views.run, name="run"),
    path("argus_app", views.read_file, name="read_file"),
]