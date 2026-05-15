from django.contrib.auth.decorators import user_passes_test


def group_required(*group_names):
    def predicate(user):
        return user.is_authenticated and (user.is_superuser or user.groups.filter(name__in=group_names).exists())

    return user_passes_test(predicate)


def front_desk_required(view_func):
    return group_required('front_desk', '前台接待')(view_func)


def route_manager_required(view_func):
    return group_required('route_manager', '路线管理员')(view_func)


def finance_clerk_required(view_func):
    return group_required('finance_clerk', '催款员工')(view_func)