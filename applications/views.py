from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.forms import formset_factory
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from applications.forms import ApplicationForm, ParticipantForm
from applications.models import Application, Participant
from tours.models import TourGroup
from users.permissions import finance_clerk_required, front_desk_required


@front_desk_required
def application_create(request, tour_group_id):
    tour_group = get_object_or_404(TourGroup, pk=tour_group_id, is_deleted=False)

    if request.method == 'POST':
        form = ApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.tour_group = tour_group
            application.save()
            if application.deposit_paid:
                application.deposit_paid_at = timezone.localdate()
                application.deposit_receipt_no = f'DP{application.id:08d}'
                application.save(update_fields=['deposit_paid_at', 'deposit_receipt_no'])
            messages.success(request, '申请单已保存，请继续录入参加者。')
            return redirect('applications:participant_entry', application_id=application.id)
    else:
        form = ApplicationForm(initial={'balance_due_date': tour_group.deadline})

    return render(request, 'applications/application_form.html', {'form': form, 'tour_group': tour_group})


@front_desk_required
def participant_entry(request, application_id):
    application = get_object_or_404(Application.objects.select_related('tour_group'), pk=application_id)
    ParticipantFormSet = formset_factory(ParticipantForm, extra=3, can_delete=False)

    if request.method == 'POST':
        formset = ParticipantFormSet(request.POST)
        if formset.is_valid():
            with transaction.atomic():
                application.participants.all().delete()
                for form in formset:
                    cleaned = form.cleaned_data
                    if not cleaned:
                        continue
                    if not cleaned.get('full_name') and not cleaned.get('id_card'):
                        continue
                    Participant.objects.create(
                        application=application,
                        full_name=cleaned['full_name'],
                        id_card=cleaned['id_card'],
                        is_contact=cleaned.get('is_contact', False),
                    )
                application.status = Application.Status.COMPLETED
                application.save(update_fields=['status'])
            messages.success(request, '参加者已保存，申请状态已更新为已完成。')
            return redirect('applications:application_detail', application_id=application.id)
    else:
        existing = list(application.participants.all())
        initial = [{'full_name': p.full_name, 'id_card': p.id_card, 'is_contact': p.is_contact} for p in existing]
        while len(initial) < 3:
            initial.append({})
        formset = ParticipantFormSet(initial=initial)

    return render(request, 'applications/participant_entry.html', {'application': application, 'formset': formset})


def application_detail(request, application_id):
    application = get_object_or_404(Application.objects.select_related('tour_group', 'tour_group__route'), pk=application_id)
    return render(request, 'applications/application_detail.html', {'application': application})


@front_desk_required
def cancel_application(request, application_id):
    application = get_object_or_404(Application.objects.select_related('tour_group'), pk=application_id)
    if request.method != 'POST':
        raise Http404

    application.status = Application.Status.CANCELED
    application.canceled_at = timezone.now()
    application.refund_amount = application.cancel_refund_amount()
    application.save(update_fields=['status', 'canceled_at', 'refund_amount'])
    messages.success(request, f'申请已取消，退款金额为 {application.refund_amount} 元。')
    return redirect('applications:application_detail', application_id=application.id)


def print_confirm(request, application_id):
    application = get_object_or_404(Application.objects.select_related('tour_group', 'tour_group__route'), pk=application_id)
    return render(request, 'applications/print_confirm.html', {'application': application})


@front_desk_required
def balance_payment_list(request):
    pending_applications = Application.objects.select_related('tour_group').filter(balance_paid=False).order_by('-created_at')

    if request.method == 'POST':
        updated_count = 0
        for application in pending_applications:
            receipt_key = f'receipt_no_{application.id}'
            amount_key = f'amount_{application.id}'
            receipt_no = request.POST.get(receipt_key, '').strip()
            amount_raw = request.POST.get(amount_key, '').strip()
            if not receipt_no and not amount_raw:
                continue
            if not receipt_no or not amount_raw:
                messages.error(request, f'申请单 {application.id} 的交款单号和金额必须同时填写。')
                continue
            application.balance_paid = True
            application.balance_receipt_no = receipt_no
            application.balance_amount = Decimal(amount_raw)
            application.balance_paid_at = timezone.localdate()
            application.save(update_fields=['balance_paid', 'balance_receipt_no', 'balance_amount', 'balance_paid_at'])
            updated_count += 1
        if updated_count:
            messages.success(request, f'已更新 {updated_count} 条余款支付记录。')
        return redirect('applications:balance_payment_list')

    return render(request, 'applications/balance_payment_list.html', {'applications': pending_applications})
