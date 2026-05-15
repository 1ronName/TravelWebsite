from django.urls import path

from .views import export_today_finance_csv

app_name = 'finance'

urlpatterns = [
    path('export-today/', export_today_finance_csv, name='export_today'),
]