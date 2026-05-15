from __future__ import annotations

from django.db import models
from django.utils import timezone


class Route(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "活跃"
        INACTIVE = "inactive", "不活跃"
        CANCELED = "canceled", "已取消"

    name = models.CharField(max_length=100, unique=True, verbose_name="路线名称")
    destination = models.CharField(max_length=100, verbose_name="目的地")
    description = models.TextField(blank=True, verbose_name="路线说明")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, verbose_name="状态")
    season = models.CharField(max_length=20, blank=True, verbose_name="季节（如：春季、夏季）")
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
        verbose_name="上级路线",
    )
    version = models.PositiveIntegerField(default=1, verbose_name="版本号")
    previous_version = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="next_versions",
        verbose_name="前一版本",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="修改时间")

    class Meta:
        db_table = "route"
        verbose_name = "路线"
        verbose_name_plural = "路线"
        ordering = ["-created_at", "destination", "name"]
        indexes = [
            models.Index(fields=["destination", "status"]),
            models.Index(fields=["name", "version"]),
        ]

    def __str__(self) -> str:
        version_str = f" v{self.version}" if self.version > 1 else ""
        return f"{self.name}{version_str} - {self.destination}"

    @property
    def is_deleted(self) -> bool:
        """向后兼容属性"""
        return self.status == self.Status.CANCELED


class TourGroup(models.Model):
    code = models.CharField(max_length=30, unique=True, verbose_name="团代码")
    route = models.ForeignKey(Route, on_delete=models.PROTECT, related_name="tour_groups", verbose_name="路线")
    start_date = models.DateField(verbose_name="出发日期")
    deadline = models.DateField(verbose_name="截止日期")
    max_capacity = models.PositiveIntegerField(verbose_name="人数限额")
    price_adult = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="大人价格")
    price_child = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="小孩价格")
    is_price_published = models.BooleanField(default=False, verbose_name="是否公开价格")
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="修改时间")

    class Meta:
        db_table = "tour_group"
        verbose_name = "旅游团"
        verbose_name_plural = "旅游团"
        ordering = ["-start_date", "code"]
        indexes = [
            models.Index(fields=["start_date", "deadline"]),
            models.Index(fields=["is_price_published", "is_deleted"]),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.route.name}"

    @property
    def is_open_for_application(self) -> bool:
        return not self.is_deleted and self.deadline >= timezone.localdate()

    def remaining_seats(self, booked_people: int = 0) -> int:
        return max(self.max_capacity - booked_people, 0)

    def save(self, *args, **kwargs):
        """保存前检查价格是否已公开，已公开则不允许改价"""
        if self.pk:  # 这是一个更新操作
            old_instance = TourGroup.objects.filter(pk=self.pk).first()
            if old_instance and old_instance.is_price_published:
                # 已公开价格，记录价格变更历史
                if (old_instance.price_adult != self.price_adult or 
                    old_instance.price_child != self.price_child):
                    # 价格被改变了，但由于是已公开的，需要保存历史并恢复原价
                    PriceChangeHistory.objects.create(
                        tour_group=old_instance,
                        old_price_adult=old_instance.price_adult,
                        old_price_child=old_instance.price_child,
                        new_price_adult=self.price_adult,
                        new_price_child=self.price_child,
                        is_rejected=True,
                        reason="价格已公开，不允许修改",
                    )
                    # 恢复原价
                    self.price_adult = old_instance.price_adult
                    self.price_child = old_instance.price_child
                    
        super().save(*args, **kwargs)


class RouteChangeHistory(models.Model):
    """路线变更历史记录"""
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="change_histories", verbose_name="路线")
    old_route = models.ForeignKey(
        Route,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="上一版本路线",
    )
    changed_field = models.CharField(max_length=50, verbose_name="变更字段")
    old_value = models.TextField(blank=True, verbose_name="原值")
    new_value = models.TextField(blank=True, verbose_name="新值")
    reason = models.TextField(blank=True, verbose_name="变更原因")
    changed_by = models.CharField(max_length=100, verbose_name="变更人")
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name="变更时间")

    class Meta:
        db_table = "route_change_history"
        verbose_name = "路线变更历史"
        verbose_name_plural = "路线变更历史"
        ordering = ["-changed_at"]

    def __str__(self) -> str:
        return f"{self.route.name} - {self.changed_field} ({self.changed_at.strftime('%Y-%m-%d')})"


class PriceChangeHistory(models.Model):
    """价格变更历史记录"""
    tour_group = models.ForeignKey(TourGroup, on_delete=models.CASCADE, related_name="price_histories", verbose_name="旅游团")
    old_price_adult = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="原成人价")
    old_price_child = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="原儿童价")
    new_price_adult = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="新成人价")
    new_price_child = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="新儿童价")
    is_rejected = models.BooleanField(default=False, verbose_name="是否被拒绝")
    reason = models.TextField(blank=True, verbose_name="原因（如已公开价格）")
    changed_by = models.CharField(max_length=100, blank=True, verbose_name="修改人")
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name="修改时间")

    class Meta:
        db_table = "price_change_history"
        verbose_name = "价格变更历史"
        verbose_name_plural = "价格变更历史"
        ordering = ["-changed_at"]

    def __str__(self) -> str:
        return f"{self.tour_group.code} - ¥{self.old_price_adult} → ¥{self.new_price_adult}"