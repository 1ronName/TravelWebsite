from django.contrib.auth.models import Group
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
    group_names = ['front_desk', 'route_manager', 'finance_clerk']
    for group_name in group_names:
        Group.objects.get_or_create(name=group_name)
