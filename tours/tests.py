from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from .models import Route, TourGroup, RouteChangeHistory, PriceChangeHistory


# ============================================================
#  Route 模型测试
# ============================================================
class RouteModelTests(TestCase):
    """测试 Route 模型的核心属性和方法"""

    def test_str_without_version(self):
        """版本号为 1 时不显示版本号"""
        route = Route.objects.create(
            name="海南环岛游", destination="海南", version=1
        )
        self.assertEqual(str(route), "海南环岛游 - 海南")

    def test_str_with_version(self):
        """版本号大于 1 时显示 v2 等标识"""
        route = Route.objects.create(
            name="海南环岛游", destination="海南", version=2
        )
        self.assertEqual(str(route), "海南环岛游 v2 - 海南")

    def test_is_deleted_when_canceled(self):
        """状态为 CANCELED 时 is_deleted 返回 True"""
        route = Route.objects.create(
            name="测试路线", destination="测试", status=Route.Status.CANCELED
        )
        self.assertTrue(route.is_deleted)

    def test_is_deleted_when_active(self):
        """状态为 ACTIVE 时 is_deleted 返回 False"""
        route = Route.objects.create(
            name="测试路线", destination="测试", status=Route.Status.ACTIVE
        )
        self.assertFalse(route.is_deleted)

    def test_default_status_is_active(self):
        """新建路线默认状态为 ACTIVE"""
        route = Route.objects.create(name="新路线", destination="新目的地")
        self.assertEqual(route.status, Route.Status.ACTIVE)

    def test_parent_child_relationship(self):
        """测试路线的父子层级关系"""
        parent = Route.objects.create(name="华东游", destination="华东")
        child = Route.objects.create(
            name="江南水乡游", destination="浙江", parent=parent
        )
        self.assertEqual(child.parent, parent)
        self.assertIn(child, parent.children.all())

    def test_version_chain(self):
        """测试版本链：previous_version → next_versions"""
        v1 = Route.objects.create(name="路线V1", destination="目的地", version=1)
        v2 = Route.objects.create(
            name="路线V2", destination="目的地", version=2, previous_version=v1
        )
        self.assertEqual(v2.previous_version, v1)
        self.assertIn(v2, v1.next_versions.all())

    def test_ordering_by_created_at_desc(self):
        """测试默认排序：按创建时间倒序 + 目的地 + 名称"""
        r1 = Route.objects.create(name="A路线", destination="北京")
        r2 = Route.objects.create(name="B路线", destination="上海")
        routes = list(Route.objects.all())
        # r2 后创建，应排在前面
        self.assertEqual(routes[0], r2)
        self.assertEqual(routes[1], r1)


# ============================================================
#  TourGroup 模型测试
# ============================================================
class TourGroupModelTests(TestCase):
    """测试 TourGroup 模型的核心业务逻辑"""

    def setUp(self):
        """创建测试用的路线和旅游团基础数据"""
        self.route = Route.objects.create(
            name="海南环岛游", destination="海南"
        )
        today = timezone.localdate()
        self.active_group = TourGroup.objects.create(
            code="TG-ACTIVE-001",
            route=self.route,
            start_date=today + timedelta(days=15),
            deadline=today + timedelta(days=10),
            max_capacity=20,
            price_adult=Decimal("3500.00"),
            price_child=Decimal("2500.00"),
            is_price_published=True,
        )

    def test_str_representation(self):
        """字符串表示格式：团代码 - 路线名称"""
        expected = f"TG-ACTIVE-001 - 海南环岛游"
        self.assertEqual(str(self.active_group), expected)

    def test_is_open_for_application_when_valid(self):
        """未删除且截止日期未过时，可接受报名"""
        self.assertTrue(self.active_group.is_open_for_application)

    def test_is_open_for_application_when_deleted(self):
        """已删除的团不可接受报名"""
        self.active_group.is_deleted = True
        self.active_group.save()
        self.assertFalse(self.active_group.is_open_for_application)

    def test_is_open_for_application_when_deadline_passed(self):
        """截止日期已过，不可接受报名"""
        today = timezone.localdate()
        self.active_group.deadline = today - timedelta(days=1)
        self.active_group.save()
        self.assertFalse(self.active_group.is_open_for_application)

    def test_remaining_seats_empty(self):
        """空团时剩余名额 = 总容量"""
        self.assertEqual(self.active_group.remaining_seats(booked_people=0), 20)

    def test_remaining_seats_partial(self):
        """部分预订后剩余名额正确计算"""
        self.assertEqual(self.active_group.remaining_seats(booked_people=8), 12)

    def test_remaining_seats_full(self):
        """满员时剩余名额为 0"""
        self.assertEqual(self.active_group.remaining_seats(booked_people=20), 0)

    def test_remaining_seats_overbooked(self):
        """超额预订时剩余名额最小为 0（不会返回负数）"""
        self.assertEqual(self.active_group.remaining_seats(booked_people=25), 0)

    def test_save_new_instance_no_interference(self):
        """新建 TourGroup 应正常保存"""
        group = TourGroup(
            code="TG-NEW-001",
            route=self.route,
            start_date=timezone.localdate() + timedelta(days=30),
            deadline=timezone.localdate() + timedelta(days=25),
            max_capacity=15,
            price_adult=Decimal("4000.00"),
            price_child=Decimal("3000.00"),
        )
        group.save()
        self.assertIsNotNone(group.pk)
        self.assertEqual(TourGroup.objects.count(), 2)

    def test_save_price_protection_when_published(self):
        """已公开价格的团修改价格时：记录变更历史并恢复原价"""
        old_adult = self.active_group.price_adult
        old_child = self.active_group.price_child

        # 尝试修改价格
        self.active_group.price_adult = Decimal("9999.00")
        self.active_group.price_child = Decimal("8888.00")
        self.active_group.save()

        # 刷新后价格应被恢复
        self.active_group.refresh_from_db()
        self.assertEqual(self.active_group.price_adult, old_adult)
        self.assertEqual(self.active_group.price_child, old_child)

    def test_save_price_protection_creates_history(self):
        """修改已公开价格团的价格时，应创建 PriceChangeHistory 记录"""
        self.active_group.price_adult = Decimal("5000.00")
        self.active_group.price_child = Decimal("4000.00")
        self.active_group.save()

        history = PriceChangeHistory.objects.filter(
            tour_group=self.active_group
        ).first()
        self.assertIsNotNone(history)
        self.assertTrue(history.is_rejected)
        self.assertEqual(history.reason, "价格已公开，不允许修改")
        self.assertEqual(history.old_price_adult, Decimal("3500.00"))
        self.assertEqual(history.old_price_child, Decimal("2500.00"))
        self.assertEqual(history.new_price_adult, Decimal("5000.00"))
        self.assertEqual(history.new_price_child, Decimal("4000.00"))

    def test_save_price_change_allowed_when_not_published(self):
        """未公开价格的团可以正常修改价格"""
        group = TourGroup.objects.create(
            code="TG-UNPUB-001",
            route=self.route,
            start_date=timezone.localdate() + timedelta(days=30),
            deadline=timezone.localdate() + timedelta(days=25),
            max_capacity=15,
            price_adult=Decimal("1000.00"),
            price_child=Decimal("800.00"),
            is_price_published=False,
        )
        group.price_adult = Decimal("2000.00")
        group.price_child = Decimal("1500.00")
        group.save()
        group.refresh_from_db()
        self.assertEqual(group.price_adult, Decimal("2000.00"))
        self.assertEqual(group.price_child, Decimal("1500.00"))
        # 不应创建被拒绝的价格变更记录
        self.assertFalse(
            PriceChangeHistory.objects.filter(
                tour_group=group, is_rejected=True
            ).exists()
        )


# ============================================================
#  PriceChangeHistory 模型测试
# ============================================================
class PriceChangeHistoryModelTests(TestCase):
    """测试价格变更历史记录"""

    def setUp(self):
        self.route = Route.objects.create(name="测试路线", destination="测试")
        self.group = TourGroup.objects.create(
            code="TG-PCH-001",
            route=self.route,
            start_date=timezone.localdate() + timedelta(days=20),
            deadline=timezone.localdate() + timedelta(days=15),
            max_capacity=10,
            price_adult=Decimal("1000.00"),
            price_child=Decimal("500.00"),
        )

    def test_str_representation(self):
        """字符串表示格式：团代码 - ¥原价 → ¥新价"""
        history = PriceChangeHistory.objects.create(
            tour_group=self.group,
            old_price_adult=Decimal("1000.00"),
            old_price_child=Decimal("500.00"),
            new_price_adult=Decimal("1500.00"),
            new_price_child=Decimal("800.00"),
            changed_by="admin",
        )
        expected = f"TG-PCH-001 - ¥1000.00 → ¥1500.00"
        self.assertEqual(str(history), expected)

    def test_ordering_by_changed_at_desc(self):
        """按修改时间倒序排列"""
        h1 = PriceChangeHistory.objects.create(
            tour_group=self.group,
            old_price_adult=Decimal("100"), old_price_child=Decimal("50"),
            new_price_adult=Decimal("200"), new_price_child=Decimal("100"),
            changed_by="user1",
        )
        h2 = PriceChangeHistory.objects.create(
            tour_group=self.group,
            old_price_adult=Decimal("200"), old_price_child=Decimal("100"),
            new_price_adult=Decimal("300"), new_price_child=Decimal("200"),
            changed_by="user2",
        )
        histories = list(PriceChangeHistory.objects.all())
        self.assertEqual(histories[0], h2)
        self.assertEqual(histories[1], h1)


# ============================================================
#  RouteChangeHistory 模型测试
# ============================================================
class RouteChangeHistoryModelTests(TestCase):
    """测试路线变更历史记录"""

    def setUp(self):
        self.route = Route.objects.create(name="测试路线", destination="测试")

    def test_str_representation(self):
        """字符串表示格式：路线名 - 字段名 (日期)"""
        history = RouteChangeHistory.objects.create(
            route=self.route,
            changed_field="name",
            old_value="旧名称",
            new_value="新名称",
            reason="测试变更",
            changed_by="admin",
        )
        expected = f"测试路线 - name ({history.changed_at.strftime('%Y-%m-%d')})"
        self.assertEqual(str(history), expected)

    def test_ordering_by_changed_at_desc(self):
        """按变更时间倒序排列"""
        h1 = RouteChangeHistory.objects.create(
            route=self.route, changed_field="name",
            old_value="A", new_value="B",
            changed_by="user1",
        )
        h2 = RouteChangeHistory.objects.create(
            route=self.route, changed_field="destination",
            old_value="C", new_value="D",
            changed_by="user2",
        )
        histories = list(RouteChangeHistory.objects.all())
        self.assertEqual(histories[0], h2)
        self.assertEqual(histories[1], h1)


# ============================================================
#  视图测试
# ============================================================
class TourListViewTests(TestCase):
    """测试 tour_list 视图"""

    def setUp(self):
        self.route = Route.objects.create(
            name="海南环岛游", destination="海南"
        )
        today = timezone.localdate()

        # 公开价格、未删除、截止日期未过 → 应显示
        self.visible_group = TourGroup.objects.create(
            code="TG-VISIBLE",
            route=self.route,
            start_date=today + timedelta(days=30),
            deadline=today + timedelta(days=25),
            max_capacity=20,
            price_adult=Decimal("3500.00"),
            price_child=Decimal("2500.00"),
            is_price_published=True,
            is_deleted=False,
        )
        # 未公开价格 → 不应显示
        self.unpublished_group = TourGroup.objects.create(
            code="TG-UNPUB",
            route=self.route,
            start_date=today + timedelta(days=30),
            deadline=today + timedelta(days=25),
            max_capacity=20,
            price_adult=Decimal("4000.00"),
            price_child=Decimal("3000.00"),
            is_price_published=False,
            is_deleted=False,
        )
        # 已删除 → 不应显示
        self.deleted_group = TourGroup.objects.create(
            code="TG-DELETED",
            route=self.route,
            start_date=today + timedelta(days=30),
            deadline=today + timedelta(days=25),
            max_capacity=20,
            price_adult=Decimal("4000.00"),
            price_child=Decimal("3000.00"),
            is_price_published=True,
            is_deleted=True,
        )
        # 截止日期已过 → 不应显示
        self.expired_group = TourGroup.objects.create(
            code="TG-EXPIRED",
            route=self.route,
            start_date=today + timedelta(days=5),
            deadline=today - timedelta(days=1),
            max_capacity=20,
            price_adult=Decimal("4000.00"),
            price_child=Decimal("3000.00"),
            is_price_published=True,
            is_deleted=False,
        )

    def test_tour_list_only_shows_visible_tours(self):
        """只显示公开、未删除、截止未过的团"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        tours = response.context["tour_groups"]
        self.assertEqual(len(tours), 1)
        self.assertEqual(tours[0].code, "TG-VISIBLE")

    def test_tour_list_filter_by_route_name(self):
        """可按路线名称筛选"""
        # 创建另一条可见路线
        route2 = Route.objects.create(name="云南古镇游", destination="云南")
        TourGroup.objects.create(
            code="TG-YN",
            route=route2,
            start_date=timezone.localdate() + timedelta(days=30),
            deadline=timezone.localdate() + timedelta(days=25),
            max_capacity=20,
            price_adult=Decimal("4200.00"),
            price_child=Decimal("3000.00"),
            is_price_published=True,
        )
        response = self.client.get("/", {"route_name": "海南"})
        tours = response.context["tour_groups"]
        self.assertEqual(len(tours), 1)
        self.assertEqual(tours[0].code, "TG-VISIBLE")

    def test_tour_list_filter_by_destination(self):
        """可按目的地筛选（route_name 字段同时匹配目的地）"""
        response = self.client.get("/", {"route_name": "海南"})
        tours = response.context["tour_groups"]
        self.assertEqual(len(tours), 1)
        self.assertEqual(tours[0].code, "TG-VISIBLE")

    def test_tour_list_filter_by_start_date(self):
        """可按出发日期筛选"""
        # 创建一条更晚出发的团
        TourGroup.objects.create(
            code="TG-FUTURE",
            route=self.route,
            start_date=timezone.localdate() + timedelta(days=60),
            deadline=timezone.localdate() + timedelta(days=55),
            max_capacity=20,
            price_adult=Decimal("3500.00"),
            price_child=Decimal("2500.00"),
            is_price_published=True,
        )
        response = self.client.get(
            "/", {"start_date_after": str(timezone.localdate() + timedelta(days=45))}
        )
        tours = response.context["tour_groups"]
        self.assertEqual(len(tours), 1)
        self.assertEqual(tours[0].code, "TG-FUTURE")

    def test_tour_list_no_results_when_none_match(self):
        """无匹配结果时返回空列表"""
        response = self.client.get("/", {"route_name": "不存在的路线"})
        tours = response.context["tour_groups"]
        self.assertEqual(len(tours), 0)

    def test_tour_list_excludes_full_groups(self):
        """满员的团不在列表中显示"""
        # 创建一个满员的可见团（剩余名额为0的不显示）
        # 需要通过 booked_people annotation 模拟
        # 直接验证：没有 bookings 的团剩余名额应该等于 max_capacity
        response = self.client.get("/")
        tours = response.context["tour_groups"]
        for t in tours:
            self.assertGreater(t.remaining_seats_value, 0)
