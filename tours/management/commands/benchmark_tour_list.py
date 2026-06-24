"""
对 tours/views.py 的 tour_list 视图进行性能基准测试。

测试维度：
    1. 执行时间（多次取平均）
    2. 数据库查询次数
    3. 响应大小
    4. Python 循环耗时（用细粒度 cProfile）
    5. 在不同数据量下的表现对比

用法：
    python manage.py benchmark_tour_list              # 默认 10 次迭代
    python manage.py benchmark_tour_list --runs 50    # 50 次迭代
    python manage.py benchmark_tour_list --profile    # 附带完整 cProfile 输出
"""
import cProfile
import io
import pstats
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.test.client import Client
from django.contrib.auth.models import User
from django.db import connection, reset_queries
from django.db.models import Count, Q, F
from django.db.models.functions import Greatest
from django.utils import timezone

from tours.models import TourGroup
from applications.models import Application


class Command(BaseCommand):
    help = '基准测试 tours/views.py 的 tour_list 视图性能'

    def add_arguments(self, parser):
        parser.add_argument('--runs', type=int, default=10, help='迭代次数')
        parser.add_argument('--profile', action='store_true', help='输出完整 cProfile 报告')
        parser.add_argument('--compare', action='store_true', help='对比优化前/后的性能差异')

    def handle(self, *args, **options):
        runs = options['runs']
        do_profile = options['profile']
        do_compare = options['compare']

        if 'testserver' not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.append('testserver')

        # 打印当前数据规模
        route_count = __import__('tours.models', fromlist=['Route']).Route.objects.count()
        group_count = TourGroup.objects.count()
        app_count = Application.objects.count()
        participant_count = __import__('applications.models', fromlist=['Participant']).Participant.objects.count()

        # 可见团数
        today = timezone.localdate()
        visible_groups = TourGroup.objects.filter(
            is_deleted=False, is_price_published=True, deadline__gte=today
        ).count()

        self.stdout.write('=' * 70)
        self.stdout.write(' tours/views.py tour_list 性能基准测试')
        self.stdout.write('=' * 70)
        self.stdout.write(f' 数据库规模:')
        self.stdout.write(f'   路线:     {route_count}')
        self.stdout.write(f'   旅游团:   {group_count}')
        self.stdout.write(f'   报名:     {app_count}')
        self.stdout.write(f'   参加者:   {participant_count}')
        self.stdout.write(f'   前台可见团: {visible_groups}')
        self.stdout.write(f' 测试迭代:   {runs} 次')
        self.stdout.write('=' * 70)

        client = Client()
        try:
            user = User.objects.filter(is_superuser=True).first()
            if user:
                client.force_login(user)
        except Exception:
            pass

        # 预热（消除冷启动影响）
        self.stdout.write('\n预热中...')
        for _ in range(3):
            client.get('/')
        self.stdout.write('预热完成\n')

        # --- 测试 1: 端到端请求耗时 ---
        self.stdout.write('【测试 1】端到端请求耗时 (Django test client)')
        times = []
        for i in range(runs):
            t0 = time.perf_counter()
            response = client.get('/')
            elapsed = (time.perf_counter() - t0) * 1000
            times.append(elapsed)
            if (i + 1) % max(1, runs // 5) == 0:
                self.stdout.write(f'  进度: {i+1}/{runs}')

        times.sort()
        avg = sum(times) / len(times)
        p50 = times[len(times) // 2]
        p95 = times[int(len(times) * 0.95)]
        p99 = times[int(len(times) * 0.99)]
        self.stdout.write(f'  平均: {avg:.1f}ms  |  P50: {p50:.1f}ms  |  P95: {p95:.1f}ms  |  P99: {p99:.1f}ms')
        self.stdout.write(f'  最快: {times[0]:.1f}ms  |  最慢: {times[-1]:.1f}ms')
        self.stdout.write(f'  响应大小: {len(response.content)} bytes')

        # --- 测试 2: 数据库查询次数 ---
        self.stdout.write('\n【测试 2】数据库查询次数')
        from django.test.utils import override_settings
        with override_settings(DEBUG=True):
            reset_queries()
            client.get('/')
            query_count = len(connection.queries)
            total_sql_time = sum(float(q['time']) for q in connection.queries) * 1000
            self.stdout.write(f'  总查询数: {query_count}')
            self.stdout.write(f'  总 SQL 耗时: {total_sql_time:.1f}ms')
            self.stdout.write(f'  查询明细:')
            for i, q in enumerate(connection.queries[:8]):
                sql_preview = q['sql'][:150].replace('\n', ' ')
                self.stdout.write(f'    [{i+1}] {q["time"]}s | {sql_preview}...')
            if len(connection.queries) > 8:
                self.stdout.write(f'    ... 还有 {len(connection.queries) - 8} 条查询')

        # --- 测试 3: 视图各阶段细分 ---
        self.stdout.write('\n【测试 3】视图内部分阶段耗时')

        # 模拟视图中的 queryset 构建
        t0 = time.perf_counter()
        queryset = (
            TourGroup.objects.select_related('route')
            .filter(
                is_deleted=False,
                is_price_published=True,
                deadline__gte=today,
            )
            .annotate(
                booked_people=Count(
                    'applications__participants',
                    filter=Q(applications__status__in=[
                        Application.Status.NEW,
                        Application.Status.PARTICIPANTS_ENTERED,
                        Application.Status.COMPLETED,
                    ]),
                    distinct=True,
                )
            )
        )
        # 触发查询评估
        list(queryset)  # 这个触发了数据库查询，但 Python 还没过滤
        db_time = (time.perf_counter() - t0) * 1000

        # Python 循环过滤阶段
        t0 = time.perf_counter()
        tour_groups = []
        discarded = 0
        for group in queryset:
            remaining = group.max_capacity - getattr(group, 'booked_people', 0)
            if remaining > 0:
                group.remaining_seats_value = remaining
                tour_groups.append(group)
            else:
                discarded += 1
        python_time = (time.perf_counter() - t0) * 1000

        # 模板渲染阶段（模拟）
        t0 = time.perf_counter()
        from django.shortcuts import render
        # 这里不做真正的 render，因为需要真实 request
        tpl_time = (time.perf_counter() - t0) * 1000

        total_fetched = len(tour_groups) + discarded
        self.stdout.write(f'  数据库查询阶段:  {db_time:.1f}ms（返回 {total_fetched} 行）')
        self.stdout.write(f'  Python 循环过滤:  {python_time:.1f}ms（保留 {len(tour_groups)} 个，丢弃 {discarded} 个）')
        if total_fetched > 0:
            self.stdout.write(f'  Python 过滤比例:  {discarded}/{total_fetched} = {100*discarded/total_fetched:.1f}% 被丢弃')

        # --- 测试 4: 与优化版对比 ---
        if do_compare:
            self.stdout.write('\n【测试 4】优化版（数据库层过滤）对比')
            t0 = time.perf_counter()
            optimized = (
                TourGroup.objects.select_related('route')
                .filter(
                    is_deleted=False,
                    is_price_published=True,
                    deadline__gte=today,
                )
                .annotate(
                    booked_people=Count(
                        'applications__participants',
                        filter=Q(applications__status__in=[
                            Application.Status.NEW,
                            Application.Status.PARTICIPANTS_ENTERED,
                            Application.Status.COMPLETED,
                        ]),
                        distinct=True,
                    ),
                    remaining_seats=Greatest(
                        F('max_capacity') - Count(
                            'applications__participants',
                            filter=Q(applications__status__in=[
                                Application.Status.NEW,
                                Application.Status.PARTICIPANTS_ENTERED,
                                Application.Status.COMPLETED,
                            ]),
                            distinct=True,
                        ), 0,
                    )
                )
                .filter(remaining_seats__gt=0)
            )
            result = list(optimized)
            opt_time = (time.perf_counter() - t0) * 1000

            self.stdout.write(f'  优化版查询耗时:  {opt_time:.1f}ms（返回 {len(result)} 行）')
            self.stdout.write(f'  节省时间:        {max(0, db_time + python_time - opt_time):.1f}ms')
            if db_time + python_time > 0:
                speedup = (db_time + python_time) / max(opt_time, 0.001)
                self.stdout.write(f'  加速比:          {speedup:.1f}x')

        # --- cProfile 详细报告 ---
        if do_profile:
            self.stdout.write('\n' + '=' * 70)
            self.stdout.write('【cProfile 完整报告】')
            self.stdout.write('=' * 70)
            pr = cProfile.Profile()
            pr.enable()
            for _ in range(5):
                client.get('/')
            pr.disable()
            s = io.StringIO()
            ps = pstats.Stats(pr, stream=s)
            ps.sort_stats('cumulative')
            ps.print_stats(30)
            self.stdout.write(s.getvalue())

        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(' 测试完成')
        self.stdout.write('=' * 70)
