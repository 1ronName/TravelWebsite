"""
性能分析管理命令：使用 cProfile 分析指定 Django 视图的性能。

用法示例：
    # 分析首页（tour_list）
    python manage.py profile_views /

    # 分析报名详情页
    python manage.py profile_views /applications/1/

    # 分析财务导出
    python manage.py profile_views /finance/export-today/

    # 分析补款列表页
    python manage.py profile_views /applications/balance-payments/

    # 分析所有关键页面
    python manage.py profile_views --all

    # 指定输出目录
    python manage.py profile_views / --output=my_profiles/

    # 限制打印的条目数
    python manage.py profile_views / --limit=50

输出：
    1. 控制台打印 Top-N 耗时函数（按 cumulative time 排序）
    2. 保存 .prof 文件到 profile_output/ 目录，可用 snakeviz/pstats 进一步分析
"""
import cProfile
import pstats
import os
import time
from io import StringIO

from django.core.management.base import BaseCommand
from django.test.client import Client
from django.contrib.auth.models import User
from django.conf import settings


# 该项目中需要分析的关键 URL
KEY_URLS = [
    ('/', '首页 - 旅行团列表'),
    ('/applications/1/', '报名详情页'),
    ('/applications/1/print/', '打印确认页'),
    ('/finance/export-today/', '财务CSV导出'),
    ('/applications/balance-payments/', '补款列表'),
]


class Command(BaseCommand):
    help = '使用 cProfile 分析 Django 视图性能'

    def add_arguments(self, parser):
        parser.add_argument('urls', nargs='*', help='要分析的 URL 路径')
        parser.add_argument('--all', action='store_true', help='分析所有关键页面')
        parser.add_argument('--output', default='profile_output', help='.prof 文件输出目录')
        parser.add_argument('--limit', type=int, default=30, help='控制台打印的条目数')
        parser.add_argument('--sort', default='cumulative',
                            choices=['cumulative', 'time', 'calls', 'ncalls', 'name'],
                            help='排序方式')

    def handle(self, *args, **options):
        urls = list(options['urls'])
        output_dir = os.path.join(settings.BASE_DIR, options['output'])
        limit = options['limit']
        sort_by = options['sort']
        os.makedirs(output_dir, exist_ok=True)

        if options['all']:
            urls = [u[0] for u in KEY_URLS]
            self.stdout.write(self.style.SUCCESS(f'分析所有 {len(urls)} 个关键页面\n'))

        if not urls:
            self.stdout.write(self.style.WARNING('请指定 URL 或使用 --all'))
            self.stdout.write('\n可用的关键页面：')
            for url, desc in KEY_URLS:
                self.stdout.write(f'  {url:40s} {desc}')
            return

        # Django test client 需要 ALLOWED_HOSTS 包含 testserver
        if 'testserver' not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.append('testserver')

        # 使用 Django test client（不经过 WSGI，但能准确反映 Django 内部性能）
        client = Client()

        # 如果有测试用户，用它登录以获得权限
        try:
            user = User.objects.filter(is_superuser=True).first()
            if user:
                client.force_login(user)
                self.stdout.write(f'已登录用户: {user.username}\n')
        except Exception:
            pass

        for url in urls:
            self.profile_url(client, url, output_dir, limit, sort_by)

    def profile_url(self, client, url, output_dir, limit, sort_by):
        self.stdout.write(f'{"="*80}')
        self.stdout.write(f'分析: {url}')
        self.stdout.write(f'{"="*80}')

        profiler = cProfile.Profile()

        try:
            profiler.enable()
            response = client.get(url)
            profiler.disable()

            status = response.status_code
            self.stdout.write(f'状态码: {status}  |  响应大小: {len(response.content)} bytes')

            if status >= 400:
                self.stdout.write(self.style.WARNING(f'警告: HTTP {status}'))

        except Exception as e:
            profiler.disable()
            self.stdout.write(self.style.ERROR(f'请求失败: {e}'))
            return

        # --- 输出 1: 控制台摘要 ---
        s = StringIO()
        stats = pstats.Stats(profiler, stream=s)
        stats.sort_stats(sort_by)
        stats.print_stats(limit)
        self.stdout.write(s.getvalue())

        # --- 输出 2: 被调用者统计（谁调用了最耗时的函数） ---
        s2 = StringIO()
        stats2 = pstats.Stats(profiler, stream=s2)
        stats2.sort_stats('cumulative')
        # 提取前5个最耗时函数，查看它们的调用者
        top_funcs = [f[0] for f in stats2.stats.items()]
        top_funcs.sort(key=lambda x: stats2.stats[x][3], reverse=True)  # cumtime
        s2.write('\n--- 前5个最耗时函数的调用者分析 ---\n')
        for func in top_funcs[:5]:
            stats2.print_callers(func)
        self.stdout.write(s2.getvalue())

        # --- 输出 3: 保存 .prof 文件 ---
        safe_name = url.strip('/').replace('/', '_') or 'index'
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        prof_file = os.path.join(output_dir, f'{safe_name}_{timestamp}.prof')
        profiler.dump_stats(prof_file)
        self.stdout.write(self.style.SUCCESS(f'\n→ 已保存: {prof_file}'))
        self.stdout.write(f'→ 用 pstats 查看: python -m pstats {prof_file}')
        self.stdout.write(f'→ 用 snakeviz 可视化: snakeviz {prof_file}\n')
