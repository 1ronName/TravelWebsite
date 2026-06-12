from django.contrib.auth.models import AnonymousUser, User, Group
from django.test import TestCase, RequestFactory, override_settings
from django.http import HttpResponse

from .permissions import (
    group_required,
    front_desk_required,
    route_manager_required,
    finance_clerk_required,
)
from .signals import create_default_groups


# ============================================================
#  权限装饰器测试
# ============================================================
class PermissionDecoratorTests(TestCase):
    """测试基于组的权限装饰器"""

    def setUp(self):
        """创建测试用户和组"""
        self.factory = RequestFactory()

        # 创建各组
        self.front_desk_group, _ = Group.objects.get_or_create(name="front_desk")
        self.route_manager_group, _ = Group.objects.get_or_create(name="route_manager")
        self.finance_clerk_group, _ = Group.objects.get_or_create(name="finance_clerk")

        # 创建不同类型的用户
        self.superuser = User.objects.create_superuser(
            username="admin", password="admin123"
        )
        self.front_desk_user = User.objects.create_user(
            username="front_user", password="test123"
        )
        self.front_desk_user.groups.add(self.front_desk_group)

        self.route_manager_user = User.objects.create_user(
            username="route_user", password="test123"
        )
        self.route_manager_user.groups.add(self.route_manager_group)

        self.finance_user = User.objects.create_user(
            username="finance_user", password="test123"
        )
        self.finance_user.groups.add(self.finance_clerk_group)

        self.no_group_user = User.objects.create_user(
            username="nobody", password="test123"
        )

    def _make_request(self, user):
        """创建带用户的模拟请求"""
        request = self.factory.get("/test/")
        request.user = user
        return request

    def dummy_view(self, request):
        return HttpResponse("OK")

    # ---------- group_required ----------
    def test_group_required_allows_matching_group(self):
        """用户属于所需组时允许访问"""
        decorated = group_required("front_desk")(self.dummy_view)
        request = self._make_request(self.front_desk_user)
        response = decorated(request)
        self.assertEqual(response.status_code, 200)

    def test_group_required_allows_superuser(self):
        """超级用户总是允许访问"""
        decorated = group_required("front_desk")(self.dummy_view)
        request = self._make_request(self.superuser)
        response = decorated(request)
        self.assertEqual(response.status_code, 200)

    def test_group_required_denies_wrong_group(self):
        """用户不属于所需组时被拒绝"""
        decorated = group_required("route_manager")(self.dummy_view)
        request = self._make_request(self.front_desk_user)
        response = decorated(request)
        # user_passes_test 对匿名/无权限用户重定向到登录页
        self.assertNotEqual(response.status_code, 200)

    def test_group_required_denies_no_group_user(self):
        """无组用户被拒绝"""
        decorated = group_required("front_desk")(self.dummy_view)
        request = self._make_request(self.no_group_user)
        response = decorated(request)
        self.assertNotEqual(response.status_code, 200)

    def test_group_required_denies_anonymous(self):
        """匿名用户被拒绝"""
        decorated = group_required("front_desk")(self.dummy_view)
        request = self.factory.get("/test/")
        request.user = AnonymousUser()  # 匿名用户 (未认证)
        response = decorated(request)
        self.assertNotEqual(response.status_code, 200)

    def test_group_required_multiple_groups(self):
        """用户属于任意一个指定组即允许"""
        decorated = group_required("front_desk", "route_manager")(self.dummy_view)
        # front_desk_user 应通过
        request = self._make_request(self.front_desk_user)
        response = decorated(request)
        self.assertEqual(response.status_code, 200)
        # route_manager_user 也应通过
        request = self._make_request(self.route_manager_user)
        response = decorated(request)
        self.assertEqual(response.status_code, 200)

    # ---------- front_desk_required ----------
    def test_front_desk_required_allows_front_desk_user(self):
        """前台接待组用户可访问"""
        decorated = front_desk_required(self.dummy_view)
        request = self._make_request(self.front_desk_user)
        response = decorated(request)
        self.assertEqual(response.status_code, 200)

    def test_front_desk_required_denies_route_manager(self):
        """路线管理员不可访问前台接口"""
        decorated = front_desk_required(self.dummy_view)
        request = self._make_request(self.route_manager_user)
        response = decorated(request)
        self.assertNotEqual(response.status_code, 200)

    # ---------- route_manager_required ----------
    def test_route_manager_required_allows_route_manager(self):
        """路线管理员组用户可访问"""
        decorated = route_manager_required(self.dummy_view)
        request = self._make_request(self.route_manager_user)
        response = decorated(request)
        self.assertEqual(response.status_code, 200)

    def test_route_manager_required_denies_front_desk(self):
        """前台用户不可访问路线管理接口"""
        decorated = route_manager_required(self.dummy_view)
        request = self._make_request(self.front_desk_user)
        response = decorated(request)
        self.assertNotEqual(response.status_code, 200)

    # ---------- finance_clerk_required ----------
    def test_finance_clerk_required_allows_finance_user(self):
        """财务组用户可访问"""
        decorated = finance_clerk_required(self.dummy_view)
        request = self._make_request(self.finance_user)
        response = decorated(request)
        self.assertEqual(response.status_code, 200)

    def test_finance_clerk_required_denies_others(self):
        """非财务用户不可访问财务接口"""
        decorated = finance_clerk_required(self.dummy_view)
        request = self._make_request(self.front_desk_user)
        response = decorated(request)
        self.assertNotEqual(response.status_code, 200)

    def test_finance_clerk_required_allows_superuser(self):
        """超级用户可访问财务接口"""
        decorated = finance_clerk_required(self.dummy_view)
        request = self._make_request(self.superuser)
        response = decorated(request)
        self.assertEqual(response.status_code, 200)


# ============================================================
#  信号测试
# ============================================================
class SignalTests(TestCase):
    """测试 post_migrate 信号"""

    def test_create_default_groups_creates_groups(self):
        """信号触发时应创建三个默认组"""
        # 直接调用信号处理函数
        create_default_groups(sender=None)

        self.assertTrue(Group.objects.filter(name="front_desk").exists())
        self.assertTrue(Group.objects.filter(name="route_manager").exists())
        self.assertTrue(Group.objects.filter(name="finance_clerk").exists())

    def test_create_default_groups_idempotent(self):
        """重复调用不会创建重复的组"""
        create_default_groups(sender=None)
        create_default_groups(sender=None)

        # 每个组还是只有 1 个
        self.assertEqual(Group.objects.filter(name="front_desk").count(), 1)
        self.assertEqual(Group.objects.filter(name="route_manager").count(), 1)
        self.assertEqual(Group.objects.filter(name="finance_clerk").count(), 1)

    def test_create_default_groups_total_count(self):
        """最终应有恰好 3 个默认组"""
        create_default_groups(sender=None)
        self.assertEqual(Group.objects.count(), 3)
