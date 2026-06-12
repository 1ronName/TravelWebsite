import csv
import io
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User, Group
from django.test import TestCase
from django.utils import timezone

from applications.models import Application
from tours.models import Route, TourGroup


class FinanceExportViewTests(TestCase):
    """测试财务导出 CSV 视图"""

    def setUp(self):
        """创建测试数据"""
        today = timezone.localdate()

        # 创建权限组和用户
        self.finance_group, _ = Group.objects.get_or_create(name="finance_clerk")
        self.finance_user = User.objects.create_user(
            username="finance_test", password="test123"
        )
        self.finance_user.groups.add(self.finance_group)

        # 创建路线和旅游团
        self.route = Route.objects.create(name="测试路线", destination="测试")
        self.tour_group = TourGroup.objects.create(
            code="TG-FIN-001",
            route=self.route,
            start_date=today + timedelta(days=30),
            deadline=today + timedelta(days=25),
            max_capacity=20,
            price_adult=Decimal("3500.00"),
            price_child=Decimal("2500.00"),
        )

    def _parse_csv_response(self, response):
        """解析 CSV 响应内容，处理 BOM"""
        content = response.content.decode("utf-8")
        # Django 的 HttpResponse 配合 csv.writer 和 utf-8-sig 编码时
        # 可能在多个位置插入 BOM，需要全部移除
        content = content.replace("﻿", "")
        reader = csv.reader(io.StringIO(content))
        return list(reader)

    def test_export_requires_permission(self):
        """匿名用户被重定向"""
        response = self.client.get("/finance/export-today/")
        self.assertEqual(response.status_code, 302)

    def test_export_returns_csv_content_type(self):
        """导出返回 CSV 内容类型"""
        self.client.force_login(self.finance_user)
        response = self.client.get("/finance/export-today/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])

    def test_export_has_content_disposition_header(self):
        """响应包含 Content-Disposition 头"""
        self.client.force_login(self.finance_user)
        response = self.client.get("/finance/export-today/")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_export_includes_today_deposit_records(self):
        """导出包含今日订金记录"""
        today = timezone.localdate()
        app = Application.objects.create(
            tour_group=self.tour_group,
            contact_name="张三",
            contact_phone="13800001111",
            deposit_paid=True,
            deposit_paid_at=today,
            deposit_amount=Decimal("700.00"),
            deposit_receipt_no="DP00000001",
        )

        self.client.force_login(self.finance_user)
        response = self.client.get("/finance/export-today/")
        rows = self._parse_csv_response(response)

        # 应有标题行 + 1 条数据
        self.assertGreaterEqual(len(rows), 2)
        data_row = rows[1]
        self.assertEqual(data_row[0], "订金")
        self.assertEqual(data_row[1], str(app.id))
        self.assertEqual(data_row[2], "TG-FIN-001")
        self.assertEqual(data_row[3], "张三")
        self.assertEqual(data_row[4], "700.00")

    def test_export_includes_today_balance_records(self):
        """导出包含今日余款记录"""
        today = timezone.localdate()
        Application.objects.create(
            tour_group=self.tour_group,
            contact_name="李四",
            contact_phone="13800002222",
            balance_paid=True,
            balance_paid_at=today,
            balance_amount=Decimal("2800.00"),
            balance_receipt_no="REC-001",
        )

        self.client.force_login(self.finance_user)
        response = self.client.get("/finance/export-today/")
        rows = self._parse_csv_response(response)

        data_rows = [r for r in rows[1:] if r]  # 跳过标题行
        self.assertGreaterEqual(len(data_rows), 1)
        self.assertTrue(
            any(r[0] == "余款" and r[3] == "李四" for r in data_rows)
        )

    def test_export_excludes_non_today_records(self):
        """不导出非今日的记录"""
        yesterday = timezone.localdate() - timedelta(days=1)
        Application.objects.create(
            tour_group=self.tour_group,
            contact_name="历史记录",
            contact_phone="13800003333",
            deposit_paid=True,
            deposit_paid_at=yesterday,  # 昨天的记录
            deposit_amount=Decimal("500.00"),
            deposit_receipt_no="DP-OLD",
        )

        self.client.force_login(self.finance_user)
        response = self.client.get("/finance/export-today/")
        rows = self._parse_csv_response(response)

        # 只有标题行，无数据
        data_rows = [r for r in rows[1:] if r]
        self.assertEqual(len(data_rows), 0)

    def test_export_empty_when_no_records(self):
        """今日无记录时只返回 CSV 标题行"""
        self.client.force_login(self.finance_user)
        response = self.client.get("/finance/export-today/")
        rows = self._parse_csv_response(response)

        # 只有标题行
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0], ["类型", "申请单ID", "团代码", "责任人", "金额", "单号", "日期"])

    def test_export_csv_header_row(self):
        """CSV 文件包含正确的标题行"""
        self.client.force_login(self.finance_user)
        response = self.client.get("/finance/export-today/")
        rows = self._parse_csv_response(response)

        self.assertEqual(
            rows[0],
            ["类型", "申请单ID", "团代码", "责任人", "金额", "单号", "日期"],
        )
