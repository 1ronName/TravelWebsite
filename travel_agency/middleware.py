"""
性能分析中间件：通过在 URL 后添加 ?profile 参数来触发 cProfile 分析。

使用方式：
    访问任意页面时在 URL 后加 ?profile，如：
    http://localhost:8000/?profile
    http://localhost:8000/applications/1/?profile

分析结果将保存在项目根目录的 profile_output/ 目录下。
"""
import cProfile
import pstats
import os
import time
from django.conf import settings
from io import StringIO


class ProfileMiddleware:
    """
    通过 ?profile 参数触发性能分析。

    激活方式：
    1. 在 settings.py 的 MIDDLEWARE 列表最前面添加：
       'travel_agency.middleware.ProfileMiddleware'
    2. 确保 DEBUG=True
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # DEBUG 模式下才允许
        if not settings.DEBUG:
            return self.get_response(request)

        # 通过 ?profile 参数触发
        if 'profile' not in request.GET:
            return self.get_response(request)

        # 创建输出目录
        output_dir = os.path.join(settings.BASE_DIR, 'profile_output')
        os.makedirs(output_dir, exist_ok=True)

        # 生成文件名：视图名_时间戳.prof
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        view_name = request.resolver_match.view_name if request.resolver_match else 'unknown'
        safe_name = view_name.replace(':', '_').replace('/', '_')
        output_file = os.path.join(output_dir, f'{safe_name}_{timestamp}.prof')

        profiler = cProfile.Profile()
        profiler.enable()

        response = self.get_response(request)

        profiler.disable()

        # 保存原始数据
        profiler.dump_stats(output_file)

        # 同时在控制台打印摘要
        s = StringIO()
        stats = pstats.Stats(profiler, stream=s)
        stats.sort_stats('cumulative')
        stats.print_stats(30)
        print(f"\n{'='*80}")
        print(f"[cProfile] 性能分析完成 → 文件: {output_file}")
        print(f"{'='*80}")
        print(s.getvalue())
        print(f"{'='*80}\n")

        return response
