from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from tours.models import Route, TourGroup

from .forms import ApplicationForm, ParticipantForm
from .models import Application, Participant


# ============================================================
#  Application 模型测试 — 属性与方法
# ============================================================
class ApplicationModelTests(TestCase):
    """测试 Application 模型的核心业务逻辑"""

    def setUp(self):
        """创建基础数据"""
        today = timezone.localdate()
        self.route = Route.objects.create(
            name="海南环岛游", destination="海南"
        )
        self.tour_group = TourGroup.objects.create(
            code="TG-APP-001",
            route=self.route,
            start_date=today + timedelta(days=30),   # 30天后出发
            deadline=today + timedelta(days=25),
            max_capacity=20,
            price_adult=Decimal("3500.00"),
            price_child=Decimal("2500.00"),
            is_price_published=True,
        )

    # ---------- 基础字段 ----------
    def test_str_representation(self):
        """字符串表示：联系人姓名 - 团代码"""
        app = Application.objects.create(
            tour_group=self.tour_group,
            contact_name="张三",
            contact_phone="13800001111",
            adult_count=2,
            child_count=1,
        )
        self.assertEqual(str(app), "张三 - TG-APP-001")

    def test_default_status_is_new(self):
        """新建申请默认状态为 NEW"""
        app = Application.objects.create(
            tour_group=self.tour_group,
            contact_name="张三",
            contact_phone="13800001111",
        )
        self.assertEqual(app.status, Application.Status.NEW)

    # ---------- participant_count ----------
    def test_participant_count(self):
        """总参加人数 = 大人数 + 小孩数"""
        app = Application.objects.create(
            tour_group=self.tour_group,
            contact_name="张三",
            contact_phone="13800001111",
            adult_count=2,
            child_count=3,
        )
        self.assertEqual(app.participant_count, 5)

    def test_participant_count_zero(self):
        """大人和小孩都为 0 时总人数为 0"""
        app = Application.objects.create(
            tour_group=self.tour_group,
            contact_name="张三",
            contact_phone="13800001111",
            adult_count=0,
            child_count=0,
        )
        self.assertEqual(app.participant_count, 0)

    # ---------- total_amount ----------
    def test_total_amount(self):
        """总价 = 成人价×成人数 + 儿童价×儿童数"""
        app = Application.objects.create(
            tour_group=self.tour_group,
            contact_name="张三",
            contact_phone="13800001111",
            adult_count=2,    # 3500 × 2 = 7000
            child_count=1,    # 2500 × 1 = 2500
        )                     # total = 9500
        self.assertEqual(app.total_amount, Decimal("9500.00"))

    def test_total_amount_zero_participants(self):
        """无参加者时总价为 0"""
        app = Application.objects.create(
            tour_group=self.tour_group,
            contact_name="张三",
            contact_phone="13800001111",
            adult_count=0,
            child_count=0,
        )
        self.assertEqual(app.total_amount, Decimal("0.00"))

    # ---------- balance_amount_due ----------
    def test_balance_amount_due_not_paid(self):
        """未付余款：余额 = 总价 - 订金"""
        app = Application.objects.create(
            tour_group=self.tour_group,
            contact_name="张三",
            contact_phone="13800001111",
            adult_count=2,
            child_count=0,
            deposit_amount=Decimal("500.00"),
            balance_paid=False,
        )
        # total = 7000, deposit = 500 → balance = 6500
        self.assertEqual(app.balance_amount_due, Decimal("6500.00"))

    def test_balance_amount_due_when_paid(self):
        """已付余款：余额为 0"""
        app = Application.objects.create(
            tour_group=self.tour_group,
            contact_name="张三",
            contact_phone="13800001111",
            adult_count=2,
            child_count=0,
            deposit_amount=Decimal("500.00"),
            balance_paid=True,
        )
        self.assertEqual(app.balance_amount_due, Decimal("0.00"))

    def test_balance_amount_due_deposit_exceeds_total(self):
        """订金超额时余额为 0（不小于0）"""
        app = Application.objects.create(
            tour_group=self.tour_group,
            contact_name="张三",
            contact_phone="13800001111",
            adult_count=1,
            child_count=0,
            deposit_amount=Decimal("5000.00"),  # 超过总价 3500
            balance_paid=False,
        )
        self.assertEqual(app.balance_amount_due, Decimal("0.00"))

    # ---------- cancel_fee_amount ----------
    def test_cancel_fee_30_days_before(self):
        """出发前 ≥30 天：手续费 0%"""
        app = Application.objects.create(
            tour_group=self.tour_group,  # start_date = today + 30
            contact_name="张三",
            contact_phone="13800001111",
            adult_count=2,   # total = 7000
            child_count=0,
        )
        self.assertEqual(app.cancel_fee_amount(), Decimal("0.00"))

    def test_cancel_fee_10_to_29_days_before(self):
        """出发前 10-29 天：手续费 20%"""
        # 创建一个 15 天后出发的团
        today = timezone.localdate()
        tg = TourGroup.objects.create(
            code="TG-15DAYS",
            route=self.route,
            start_date=today + timedelta(days=15),
            deadline=today + timedelta(days=10),
            max_capacity=20,
            price_adult=Decimal("1000.00"),
            price_child=Decimal("500.00"),
        )
        app = Application.objects.create(
            tour_group=tg,
            contact_name="李四",
            contact_phone="13800002222",
            adult_count=1,    # total = 1000
            child_count=0,
        )
        # 15天 → 20% × 1000 = 200
        self.assertEqual(app.cancel_fee_amount(), Decimal("200.00"))

    def test_cancel_fee_1_to_9_days_before(self):
        """出发前 1-9 天：手续费 50%"""
        today = timezone.localdate()
        tg = TourGroup.objects.create(
            code="TG-5DAYS",
            route=self.route,
            start_date=today + timedelta(days=5),
            deadline=today + timedelta(days=3),
            max_capacity=20,
            price_adult=Decimal("1000.00"),
            price_child=Decimal("500.00"),
        )
        app = Application.objects.create(
            tour_group=tg,
            contact_name="王五",
            contact_phone="13800003333",
            adult_count=1,    # total = 1000
            child_count=0,
        )
        # 5天 → 50% × 1000 = 500
        self.assertEqual(app.cancel_fee_amount(), Decimal("500.00"))

    def test_cancel_fee_departure_day(self):
        """出发当天或之后：手续费 100%"""
        today = timezone.localdate()
        tg = TourGroup.objects.create(
            code="TG-TODAY",
            route=self.route,
            start_date=today,  # 今天出发
            deadline=today - timedelta(days=1),
            max_capacity=20,
            price_adult=Decimal("1000.00"),
            price_child=Decimal("500.00"),
        )
        app = Application.objects.create(
            tour_group=tg,
            contact_name="赵六",
            contact_phone="13800004444",
            adult_count=2,   # total = 2000
            child_count=0,
        )
        # 0天 → 100%
        self.assertEqual(app.cancel_fee_amount(), Decimal("2000.00"))

    # ---------- cancel_refund_amount ----------
    def test_cancel_refund_amount(self):
        """退款金额 = 总价 - 手续费"""
        today = timezone.localdate()
        tg = TourGroup.objects.create(
            code="TG-15DAYS-REFUND",
            route=self.route,
            start_date=today + timedelta(days=15),
            deadline=today + timedelta(days=10),
            max_capacity=20,
            price_adult=Decimal("1000.00"),
            price_child=Decimal("500.00"),
        )
        app = Application.objects.create(
            tour_group=tg,
            contact_name="钱七",
            contact_phone="13800005555",
            adult_count=1,  # total = 1000
            child_count=0,
        )
        # 15天: fee=200, refund=800
        self.assertEqual(app.cancel_refund_amount(), Decimal("800.00"))

    # ---------- calc_deposit (classmethod) ----------
    def test_calc_deposit_60_days_before(self):
        """出发前 ≥60 天：订金 10%"""
        today = timezone.localdate()
        tg = TourGroup.objects.create(
            code="TG-60DAYS",
            route=self.route,
            start_date=today + timedelta(days=90),
            deadline=today + timedelta(days=85),
            max_capacity=20,
            price_adult=Decimal("1000.00"),
            price_child=Decimal("500.00"),
        )
        deposit = Application.calc_deposit(tg, adult_count=2, child_count=1)
        # total = 2500, 10% = 250
        self.assertEqual(deposit, Decimal("250.00"))

    def test_calc_deposit_30_to_59_days_before(self):
        """出发前 30-59 天：订金 20%"""
        today = timezone.localdate()
        tg = TourGroup.objects.create(
            code="TG-45DAYS",
            route=self.route,
            start_date=today + timedelta(days=45),
            deadline=today + timedelta(days=40),
            max_capacity=20,
            price_adult=Decimal("1000.00"),
            price_child=Decimal("500.00"),
        )
        deposit = Application.calc_deposit(tg, adult_count=2, child_count=0)
        # total = 2000, 20% = 400
        self.assertEqual(deposit, Decimal("400.00"))

    def test_calc_deposit_less_than_30_days(self):
        """出发前 <30 天：订金 100%（全款）"""
        today = timezone.localdate()
        tg = TourGroup.objects.create(
            code="TG-10DAYS",
            route=self.route,
            start_date=today + timedelta(days=10),
            deadline=today + timedelta(days=5),
            max_capacity=20,
            price_adult=Decimal("1000.00"),
            price_child=Decimal("500.00"),
        )
        deposit = Application.calc_deposit(tg, adult_count=1, child_count=0)
        # total = 1000, 100% = 1000
        self.assertEqual(deposit, Decimal("1000.00"))

    def test_calc_deposit_boundary_60_days(self):
        """边界值：恰好 60 天按 ≥60 天规则（10%）"""
        today = timezone.localdate()
        tg = TourGroup.objects.create(
            code="TG-EXACT60",
            route=self.route,
            start_date=today + timedelta(days=60),
            deadline=today + timedelta(days=55),
            max_capacity=20,
            price_adult=Decimal("1000.00"),
            price_child=Decimal("0.00"),
        )
        deposit = Application.calc_deposit(tg, adult_count=1, child_count=0)
        self.assertEqual(deposit, Decimal("100.00"))  # 10%

    def test_calc_deposit_boundary_30_days(self):
        """边界值：恰好 30 天按 ≥30 天规则（20%）"""
        today = timezone.localdate()
        tg = TourGroup.objects.create(
            code="TG-EXACT30",
            route=self.route,
            start_date=today + timedelta(days=30),
            deadline=today + timedelta(days=25),
            max_capacity=20,
            price_adult=Decimal("1000.00"),
            price_child=Decimal("0.00"),
        )
        deposit = Application.calc_deposit(tg, adult_count=1, child_count=0)
        self.assertEqual(deposit, Decimal("200.00"))  # 20%

    # ---------- save() 自动计算 ----------
    def test_save_auto_calculates_deposit(self):
        """保存时自动计算订金金额"""
        app = Application(
            tour_group=self.tour_group,  # 30天 → deposit 20%
            contact_name="张三",
            contact_phone="13800001111",
            adult_count=1,
            child_count=0,
        )
        app.save()
        # total=3500, 30天 → 20% = 700
        self.assertEqual(app.deposit_amount, Decimal("700.00"))

    def test_save_auto_sets_balance_due_date(self):
        """保存时自动将余款期限设为团截止日期"""
        app = Application(
            tour_group=self.tour_group,
            contact_name="张三",
            contact_phone="13800001111",
        )
        app.save()
        self.assertEqual(app.balance_due_date, self.tour_group.deadline)

    def test_save_auto_calculates_balance_when_paid(self):
        """余额付清时自动计算余额金额"""
        app = Application(
            tour_group=self.tour_group,
            contact_name="张三",
            contact_phone="13800001111",
            adult_count=1,
            child_count=0,
            balance_paid=True,
        )
        app.save()
        # total=3500, deposit自动=700, balance=2800
        self.assertEqual(app.balance_amount, Decimal("2800.00"))

    def test_save_does_not_overwrite_existing_deposit(self):
        """已有订金金额时不被覆盖"""
        app = Application.objects.create(
            tour_group=self.tour_group,
            contact_name="张三",
            contact_phone="13800001111",
            deposit_amount=Decimal("999.00"),
            adult_count=2,
            child_count=1,
        )
        self.assertEqual(app.deposit_amount, Decimal("999.00"))


# ============================================================
#  Participant 模型测试
# ============================================================
class ParticipantModelTests(TestCase):
    """测试参加者模型"""

    def setUp(self):
        route = Route.objects.create(name="测试路线", destination="测试")
        self.tour_group = TourGroup.objects.create(
            code="TG-PAR-001",
            route=route,
            start_date=timezone.localdate() + timedelta(days=30),
            deadline=timezone.localdate() + timedelta(days=25),
            max_capacity=20,
            price_adult=Decimal("3500.00"),
            price_child=Decimal("2500.00"),
        )
        self.application = Application.objects.create(
            tour_group=self.tour_group,
            contact_name="张三",
            contact_phone="13800001111",
        )

    def test_str_representation(self):
        """字符串表示格式：姓名 - 证件号"""
        p = Participant.objects.create(
            application=self.application,
            full_name="张三",
            id_card="110101198001011234",
        )
        self.assertEqual(str(p), "张三 - 110101198001011234")

    def test_is_contact_defaults_false(self):
        """is_contact 默认为 False"""
        p = Participant.objects.create(
            application=self.application,
            full_name="张三",
            id_card="110101198001011234",
        )
        self.assertFalse(p.is_contact)

    def test_unique_constraint_application_id_card(self):
        """同一申请单下证件号不可重复"""
        Participant.objects.create(
            application=self.application,
            full_name="张三",
            id_card="110101198001011234",
        )
        with self.assertRaises(Exception):
            Participant.objects.create(
                application=self.application,
                full_name="张三 Dup",
                id_card="110101198001011234",  # 同证件号
            )

    def test_same_id_card_different_application_allowed(self):
        """不同申请单可以使用相同证件号"""
        app2 = Application.objects.create(
            tour_group=self.tour_group,
            contact_name="李四",
            contact_phone="13800002222",
        )
        Participant.objects.create(
            application=self.application,
            full_name="张三",
            id_card="110101198001011234",
        )
        # 不同申请单，相同证件号应允许
        p2 = Participant.objects.create(
            application=app2,
            full_name="张三",
            id_card="110101198001011234",
        )
        self.assertIsNotNone(p2.pk)

    def test_ordering_contact_first(self):
        """联系人排在参加者列表前面"""
        p1 = Participant.objects.create(
            application=self.application,
            full_name="普通参加者",
            id_card="110101198001011111",
            is_contact=False,
        )
        p2 = Participant.objects.create(
            application=self.application,
            full_name="联系人",
            id_card="110101198001012222",
            is_contact=True,
        )
        # 通过 application.participants 查询
        participants = list(self.application.participants.all())
        self.assertEqual(participants[0], p2)  # 联系人排前面
        self.assertEqual(participants[1], p1)


# ============================================================
#  表单测试
# ============================================================
class ApplicationFormTests(TestCase):
    """测试 ApplicationForm"""

    def setUp(self):
        self.route = Route.objects.create(name="测试路线", destination="测试")
        self.tour_group = TourGroup.objects.create(
            code="TG-FORM-001",
            route=self.route,
            start_date=timezone.localdate() + timedelta(days=30),
            deadline=timezone.localdate() + timedelta(days=25),
            max_capacity=20,
            price_adult=Decimal("3500.00"),
            price_child=Decimal("2500.00"),
        )

    def test_form_valid_with_minimal_data(self):
        """表单最少必填字段验证通过"""
        form = ApplicationForm(data={
            "contact_name": "张三",
            "gender": "male",
            "contact_phone": "13800001111",
            "adult_count": 1,
            "child_count": 0,
        })
        self.assertTrue(form.is_valid())

    def test_form_invalid_without_contact_name(self):
        """缺少联系人姓名的表单不通过"""
        form = ApplicationForm(data={
            "contact_phone": "13800001111",
            "adult_count": 1,
            "child_count": 0,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("contact_name", form.errors)

    def test_form_invalid_without_contact_phone(self):
        """缺少电话号码的表单不通过"""
        form = ApplicationForm(data={
            "contact_name": "张三",
            "adult_count": 1,
            "child_count": 0,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("contact_phone", form.errors)

    def test_form_save_creates_application(self):
        """表单保存创建 Application 实例"""
        form = ApplicationForm(data={
            "contact_name": "张三",
            "gender": "male",
            "contact_phone": "13800001111",
            "adult_count": 2,
            "child_count": 1,
            "deposit_paid": False,
        })
        self.assertTrue(form.is_valid())
        app = form.save(commit=False)
        app.tour_group = self.tour_group
        app.save()
        self.assertEqual(Application.objects.count(), 1)
        self.assertEqual(app.contact_name, "张三")
        self.assertEqual(app.adult_count, 2)
        self.assertEqual(app.child_count, 1)


class ParticipantFormTests(TestCase):
    """测试 ParticipantForm"""

    def setUp(self):
        self.route = Route.objects.create(name="测试路线", destination="测试")
        self.tour_group = TourGroup.objects.create(
            code="TG-PFORM-001",
            route=self.route,
            start_date=timezone.localdate() + timedelta(days=30),
            deadline=timezone.localdate() + timedelta(days=25),
            max_capacity=20,
            price_adult=Decimal("3500.00"),
            price_child=Decimal("2500.00"),
        )
        self.application = Application.objects.create(
            tour_group=self.tour_group,
            contact_name="张三",
            contact_phone="13800001111",
        )

    def test_form_valid_with_data(self):
        """填写姓名和证件号时表单有效"""
        form = ParticipantForm(data={
            "full_name": "李四",
            "id_card": "110101198001011234",
            "is_contact": False,
        })
        self.assertTrue(form.is_valid())

    def test_form_requires_full_name(self):
        """参加者表单要求姓名字段不为空（ModelForm 默认行为）"""
        form = ParticipantForm(data={
            "full_name": "",
            "id_card": "110101198001011234",
            "is_contact": False,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("full_name", form.errors)


# ============================================================
#  视图测试
# ============================================================
class ViewTestMixin:
    """为视图测试提供辅助方法"""

    def _create_front_desk_user(self):
        """创建并登录前台接待用户"""
        from django.contrib.auth.models import User, Group
        group, _ = Group.objects.get_or_create(name="front_desk")
        user = User.objects.create_user(
            username="front_test", password="test123"
        )
        user.groups.add(group)
        self.client.force_login(user)
        return user


class ApplicationDetailViewTests(TestCase):
    """application_detail 视图（公开访问）"""

    def setUp(self):
        self.route = Route.objects.create(name="测试路线", destination="测试")
        self.tour_group = TourGroup.objects.create(
            code="TG-VIEW-001",
            route=self.route,
            start_date=timezone.localdate() + timedelta(days=30),
            deadline=timezone.localdate() + timedelta(days=25),
            max_capacity=20,
            price_adult=Decimal("3500.00"),
            price_child=Decimal("2500.00"),
        )
        self.application = Application.objects.create(
            tour_group=self.tour_group,
            contact_name="张三",
            contact_phone="13800001111",
            adult_count=2,
            child_count=1,
        )

    def test_detail_view_returns_200(self):
        """详情页返回 200"""
        response = self.client.get(
            f"/applications/{self.application.id}/"
        )
        self.assertEqual(response.status_code, 200)

    def test_detail_view_contains_application(self):
        """详情页包含申请单数据"""
        response = self.client.get(
            f"/applications/{self.application.id}/"
        )
        self.assertEqual(response.context["application"], self.application)

    def test_detail_view_404_for_invalid_id(self):
        """不存在的 ID 返回 404"""
        response = self.client.get("/applications/99999/")
        self.assertEqual(response.status_code, 404)


class PrintConfirmViewTests(TestCase):
    """print_confirm 视图（公开访问）"""

    def setUp(self):
        self.route = Route.objects.create(name="测试路线", destination="测试")
        self.tour_group = TourGroup.objects.create(
            code="TG-PRINT-001",
            route=self.route,
            start_date=timezone.localdate() + timedelta(days=30),
            deadline=timezone.localdate() + timedelta(days=25),
            max_capacity=20,
            price_adult=Decimal("3500.00"),
            price_child=Decimal("2500.00"),
        )
        self.application = Application.objects.create(
            tour_group=self.tour_group,
            contact_name="张三",
            contact_phone="13800001111",
        )

    def test_print_view_returns_200(self):
        """打印确认页返回 200"""
        response = self.client.get(
            f"/applications/{self.application.id}/print/"
        )
        self.assertEqual(response.status_code, 200)


class ApplicationCreateViewTests(ViewTestMixin, TestCase):
    """application_create 视图（需要前台权限）"""

    def setUp(self):
        self.route = Route.objects.create(name="测试路线", destination="测试")
        self.tour_group = TourGroup.objects.create(
            code="TG-CREATE-001",
            route=self.route,
            start_date=timezone.localdate() + timedelta(days=30),
            deadline=timezone.localdate() + timedelta(days=25),
            max_capacity=20,
            price_adult=Decimal("3500.00"),
            price_child=Decimal("2500.00"),
        )

    def test_create_view_redirects_anonymous(self):
        """匿名用户被重定向"""
        response = self.client.get(
            f"/applications/create/{self.tour_group.id}/"
        )
        self.assertEqual(response.status_code, 302)

    def test_create_view_get_returns_form(self):
        """GET 请求返回表单页面"""
        self._create_front_desk_user()
        response = self.client.get(
            f"/applications/create/{self.tour_group.id}/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertIn("tour_group", response.context)

    def test_create_view_post_creates_application(self):
        """POST 请求创建申请单"""
        self._create_front_desk_user()
        response = self.client.post(
            f"/applications/create/{self.tour_group.id}/",
            data={
                "contact_name": "李四",
                "gender": "female",
                "contact_phone": "13900001111",
                "adult_count": 2,
                "child_count": 0,
                "deposit_paid": False,
            },
        )
        self.assertEqual(response.status_code, 302)  # 重定向到参加者录入
        self.assertEqual(Application.objects.count(), 1)
        app = Application.objects.first()
        self.assertEqual(app.contact_name, "李四")
        self.assertEqual(app.tour_group, self.tour_group)

    def test_create_view_post_with_deposit_paid(self):
        """POST 创建时若已付订金，生成交款单号"""
        self._create_front_desk_user()
        response = self.client.post(
            f"/applications/create/{self.tour_group.id}/",
            data={
                "contact_name": "王五",
                "gender": "male",
                "contact_phone": "13700001111",
                "adult_count": 1,
                "child_count": 0,
                "deposit_paid": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        app = Application.objects.first()
        self.assertTrue(app.deposit_paid)
        self.assertIsNotNone(app.deposit_paid_at)
        self.assertTrue(app.deposit_receipt_no.startswith("DP"))

    def test_create_view_404_for_deleted_group(self):
        """已删除的团不可创建申请"""
        self._create_front_desk_user()
        self.tour_group.is_deleted = True
        self.tour_group.save()
        response = self.client.get(
            f"/applications/create/{self.tour_group.id}/"
        )
        self.assertEqual(response.status_code, 404)


class CancelApplicationViewTests(ViewTestMixin, TestCase):
    """cancel_application 视图（需要前台权限）"""

    def setUp(self):
        self.route = Route.objects.create(name="测试路线", destination="测试")
        self.tour_group = TourGroup.objects.create(
            code="TG-CANCEL-001",
            route=self.route,
            start_date=timezone.localdate() + timedelta(days=30),
            deadline=timezone.localdate() + timedelta(days=25),
            max_capacity=20,
            price_adult=Decimal("3500.00"),
            price_child=Decimal("2500.00"),
        )
        self.application = Application.objects.create(
            tour_group=self.tour_group,
            contact_name="张三",
            contact_phone="13800001111",
            adult_count=1,
            child_count=0,
        )

    def test_cancel_only_allows_post(self):
        """取消操作只接受 POST 请求"""
        self._create_front_desk_user()
        response = self.client.get(
            f"/applications/{self.application.id}/cancel/"
        )
        self.assertEqual(response.status_code, 404)

    def test_cancel_updates_status_and_refund(self):
        """取消后状态更新并计算退款"""
        self._create_front_desk_user()
        response = self.client.post(
            f"/applications/{self.application.id}/cancel/"
        )
        self.assertEqual(response.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.CANCELED)
        self.assertIsNotNone(self.application.canceled_at)
        self.assertIsNotNone(self.application.refund_amount)

    def test_cancel_requires_permission(self):
        """匿名用户不可取消申请"""
        response = self.client.post(
            f"/applications/{self.application.id}/cancel/"
        )
        self.assertEqual(response.status_code, 302)
        self.application.refresh_from_db()
        self.assertNotEqual(self.application.status, Application.Status.CANCELED)


class BalancePaymentListViewTests(ViewTestMixin, TestCase):
    """balance_payment_list 视图（需要前台权限）"""

    def setUp(self):
        self.route = Route.objects.create(name="测试路线", destination="测试")
        self.tour_group = TourGroup.objects.create(
            code="TG-BAL-001",
            route=self.route,
            start_date=timezone.localdate() + timedelta(days=30),
            deadline=timezone.localdate() + timedelta(days=25),
            max_capacity=20,
            price_adult=Decimal("3500.00"),
            price_child=Decimal("2500.00"),
        )
        self.unpaid_app = Application.objects.create(
            tour_group=self.tour_group,
            contact_name="未付款者",
            contact_phone="13800001111",
            balance_paid=False,
        )
        self.paid_app = Application.objects.create(
            tour_group=self.tour_group,
            contact_name="已付款者",
            contact_phone="13800002222",
            balance_paid=True,
        )

    def test_get_shows_unpaid_applications(self):
        """GET 请求只显示未付余款的申请"""
        self._create_front_desk_user()
        response = self.client.get("/applications/balance-payments/")
        self.assertEqual(response.status_code, 200)
        apps = response.context["applications"]
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0], self.unpaid_app)

    def test_post_marks_balance_as_paid(self):
        """POST 请求标记余款已付"""
        self._create_front_desk_user()
        response = self.client.post(
            "/applications/balance-payments/",
            data={
                f"receipt_no_{self.unpaid_app.id}": "REC-001",
                f"amount_{self.unpaid_app.id}": "2800.00",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.unpaid_app.refresh_from_db()
        self.assertTrue(self.unpaid_app.balance_paid)
        self.assertEqual(self.unpaid_app.balance_receipt_no, "REC-001")
        self.assertEqual(self.unpaid_app.balance_amount, Decimal("2800.00"))
        self.assertIsNotNone(self.unpaid_app.balance_paid_at)

    def test_post_requires_both_receipt_and_amount(self):
        """交款单号和金额必须同时填写"""
        self._create_front_desk_user()
        response = self.client.post(
            "/applications/balance-payments/",
            data={
                f"receipt_no_{self.unpaid_app.id}": "REC-001",
                # 缺少 amount
            },
        )
        self.assertEqual(response.status_code, 302)
        self.unpaid_app.refresh_from_db()
        self.assertFalse(self.unpaid_app.balance_paid)

    def test_requires_permission(self):
        """匿名用户被重定向"""
        response = self.client.get("/applications/balance-payments/")
        self.assertEqual(response.status_code, 302)
