import csv

from django.http import HttpResponse
from django.utils import timezone

from applications.models import Application
from users.permissions import finance_clerk_required


@finance_clerk_required
def export_today_finance_csv(request):
    today = timezone.localdate()
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="finance_{today:%Y%m%d}.csv"'

    writer = csv.writer(response)
    writer.writerow(['类型', '申请单ID', '团代码', '责任人', '金额', '单号', '日期'])

    deposit_records = Application.objects.select_related('tour_group').filter(deposit_paid=True, deposit_paid_at=today)
    for application in deposit_records:
        writer.writerow([
            '订金',
            application.id,
            application.tour_group.code,
            application.contact_name,
            application.deposit_amount,
            application.deposit_receipt_no,
            application.deposit_paid_at,
        ])

    balance_records = Application.objects.select_related('tour_group').filter(balance_paid=True, balance_paid_at=today)
    for application in balance_records:
        writer.writerow([
            '余款',
            application.id,
            application.tour_group.code,
            application.contact_name,
            application.balance_amount,
            application.balance_receipt_no,
            application.balance_paid_at,
        ])

    return response
