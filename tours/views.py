from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from applications.models import Application

from .models import TourGroup

ITEMS_PER_PAGE = 20


def tour_list(request):
    queryset = (
        TourGroup.objects.select_related('route')
        .filter(
            is_deleted=False,
            is_price_published=True,  # 只显示已公开价格的团
            deadline__gte=timezone.localdate()
        )
        .annotate(
            booked_people=Count(
                'applications__participants',
                filter=Q(applications__status__in=[Application.Status.NEW, Application.Status.PARTICIPANTS_ENTERED, Application.Status.COMPLETED]),
                distinct=True,
            )
        )
    )

    route_name = request.GET.get('route_name', '').strip()
    start_date_after = request.GET.get('start_date_after', '').strip()

    if route_name:
        queryset = queryset.filter(Q(route__name__icontains=route_name) | Q(route__destination__icontains=route_name))
    if start_date_after:
        queryset = queryset.filter(start_date__gte=start_date_after)

    tour_groups = []
    for group in queryset:
        remaining = group.max_capacity - getattr(group, 'booked_people', 0)
        if remaining > 0:
            group.remaining_seats_value = remaining
            tour_groups.append(group)

    paginator = Paginator(tour_groups, ITEMS_PER_PAGE)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'tours/tour_list.html', {
        'tour_groups': page_obj.object_list,
        'page_obj': page_obj,
    })