from django.urls import path

from .views import tour_list

app_name = 'tours'

urlpatterns = [
    path('', tour_list, name='tour_list'),
]