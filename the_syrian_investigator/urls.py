from django.urls import path
from . import views

urlpatterns = [
    path('investigator/', views.investigator_home, name='investigator_home'),
]