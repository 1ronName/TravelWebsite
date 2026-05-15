from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils import timezone

from tours.models import TourGroup


class Application(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "新建"
        PARTICIPANTS_ENTERED = "participants_entered", "已录入参加者"
        COMPLETED = "completed", "已完成"
        CANCELED = "canceled", "已取消"

    class Gender(models.TextChoices):
        MALE = "male", "男"
        FEMALE = "female", "女"
        OTHER = "other", "其他"

    # 基本信息
    tour_group = models.ForeignKey(TourGroup, on_delete=models.PROTECT, related_name="applications", verbose_name="旅游团")
    contact_name = models.CharField(max_length=50, verbose_name="姓名")
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.OTHER, verbose_name="性别")
    birth_date = models.DateField(null=True, blank=True, verbose_name="出生日期")
    contact_phone = models.CharField(max_length=20, verbose_name="电话号码")
    contact_address = models.CharField(max_length=200, blank=True, verbose_name="联系地址")
    email = models.EmailField(blank=True, verbose_name="Email")
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="邮政编码")
    
    # 紧急联系人
    emergency_contact_name = models.CharField(max_length=50, blank=True, verbose_name="紧急联系人姓名")
    emergency_contact_relation = models.CharField(max_length=20, blank=True, verbose_name="与本人关系")
    emergency_contact_address = models.CharField(max_length=200, blank=True, verbose_name="紧急联系地址")
    emergency_contact_phone = models.CharField(max_length=20, blank=True, verbose_name="紧急联系电话")

    # 旅行人数
    adult_count = models.PositiveIntegerField(default=0, verbose_name="大人人数")
    child_count = models.PositiveIntegerField(default=0, verbose_name="小孩人数")
    
    # 订金相关
    deposit_paid = models.BooleanField(default=False, verbose_name="订金是否已付")
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), verbose_name="订金金额")
    deposit_receipt_no = models.CharField(max_length=50, blank=True, verbose_name="订金交款单号")
    deposit_paid_at = models.DateField(null=True, blank=True, verbose_name="订金支付日期")
    
    # 余款相关
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.NEW, verbose_name="状态")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    balance_paid = models.BooleanField(default=False, verbose_name="余款是否已付")
    balance_receipt_no = models.CharField(max_length=50, blank=True, verbose_name="余款交款单号")
    balance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), verbose_name="余款金额")
    balance_paid_at = models.DateField(null=True, blank=True, verbose_name="余款支付日期")
    balance_due_date = models.DateField(null=True, blank=True, verbose_name="余款期限")
    
    # 取消相关
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), verbose_name="退款金额")
    canceled_at = models.DateTimeField(null=True, blank=True, verbose_name="取消时间")

    class Meta:
        db_table = "application"
        verbose_name = "申请单"
        verbose_name_plural = "申请单"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "deposit_paid", "balance_paid"]),
        ]

    def __str__(self) -> str:
        return f"{self.contact_name} - {self.tour_group.code}"

    @property
    def participant_count(self) -> int:
        return self.adult_count + self.child_count

    @property
    def total_amount(self) -> Decimal:
        adult_total = self.tour_group.price_adult * Decimal(self.adult_count)
        child_total = self.tour_group.price_child * Decimal(self.child_count)
        return adult_total + child_total

    @property
    def balance_amount_due(self) -> Decimal:
        if self.balance_paid:
            return Decimal("0.00")
        return max(self.total_amount - self.deposit_amount, Decimal("0.00"))

    def cancel_fee_amount(self) -> Decimal:
        """取消手续费计算
        ≥30天（1个月以上）：无（0%）
        10-29天（1个月到10天）：20%
        1-9天（10天到1天）：50%
        ≤0天（出发当天）：全款（100%）
        """
        days_before_departure = (self.tour_group.start_date - timezone.localtime()).days
        if days_before_departure >= 30:
            ratio = Decimal("0.00")
        elif days_before_departure >= 10:
            ratio = Decimal("0.20")
        elif days_before_departure >= 1:
            ratio = Decimal("0.50")
        else:
            ratio = Decimal("1.00")
        return (self.total_amount * ratio).quantize(Decimal("0.01"))

    def cancel_refund_amount(self) -> Decimal:
        return (self.total_amount - self.cancel_fee_amount()).quantize(Decimal("0.01"))

    @classmethod
    def calc_deposit(cls, tour_group: TourGroup, adult_count: int, child_count: int) -> Decimal:
        """按出发日期前的天数计算订金比例
        ≥60天（2个月）：总价的10%
        30-59天（1个月-2个月）：总价的20%
        <30天（1个月以内）：总价的100%（全款）
        """
        days_before_departure = (tour_group.start_date - timezone.localdate()).days
        adult_total = tour_group.price_adult * Decimal(adult_count)
        child_total = tour_group.price_child * Decimal(child_count)
        total_price = adult_total + child_total
        
        if days_before_departure >= 60:
            ratio = Decimal("0.10")
        elif days_before_departure >= 30:
            ratio = Decimal("0.20")
        else:
            ratio = Decimal("1.00")
        
        return (total_price * ratio).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs):
        if not self.deposit_amount:
            self.deposit_amount = self.calc_deposit(self.tour_group, self.adult_count, self.child_count)
        if not self.balance_due_date:
            self.balance_due_date = self.tour_group.deadline
        if self.balance_paid and not self.balance_amount:
            self.balance_amount = self.balance_amount_due
        super().save(*args, **kwargs)


class Participant(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="participants", verbose_name="申请单")
    full_name = models.CharField(max_length=50, verbose_name="姓名")
    id_card = models.CharField(max_length=30, verbose_name="证件号")
    is_contact = models.BooleanField(default=False, verbose_name="是否联系人")

    class Meta:
        db_table = "participant"
        verbose_name = "参加者"
        verbose_name_plural = "参加者"
        ordering = ["application_id", "-is_contact", "id"]
        constraints = [
            models.UniqueConstraint(fields=["application", "id_card"], name="uniq_application_id_card"),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} - {self.id_card}"
