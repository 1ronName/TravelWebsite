from django.urls import path

from .views import (
	application_create,
	application_detail,
	balance_payment_list,
	cancel_application,
	participant_entry,
	print_confirm,
)

app_name = 'applications'

urlpatterns = [
	path('create/<int:tour_group_id>/', application_create, name='application_create'),
	path('<int:application_id>/', application_detail, name='application_detail'),
	path('<int:application_id>/participants/', participant_entry, name='participant_entry'),
	path('<int:application_id>/print/', print_confirm, name='print_confirm'),
	path('<int:application_id>/cancel/', cancel_application, name='cancel_application'),
	path('balance-payments/', balance_payment_list, name='balance_payment_list'),
]
