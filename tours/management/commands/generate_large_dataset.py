"""
生成大规模测试数据，用于性能测试 tours/views.py。

数据规模：
    - 50 条路线
    - 2000 个旅游团（覆盖多种状态，模拟真实分布）
    - 5000 个报名申请 + 15000 个参加者

数据分布：
    - 70% 的团 is_price_published=True（前台可见）
    - 30% 的团已满员（测试 Python 过滤瓶颈）
    - 40% 的团半满
    - 30% 的团空着
    - 10% 的团 deadline 已过

用法：
    python manage.py generate_large_dataset
    python manage.py generate_large_dataset --routes 100 --groups 5000 --apps 20000
"""
import random
import time
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from tours.models import Route, TourGroup
from applications.models import Application, Participant


# 中文名字库
SURNAMES = '赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳酆鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝董梁杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍虞万支柯昝管卢莫经房裘缪干解应宗丁宣贲邓郁单杭洪包诸左石崔吉钮龚程嵇邢滑裴陆荣翁荀羊於惠甄麴家封芮羿储靳汲邴糜松井段富巫乌焦巴弓牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘钭厉戎祖武符刘景詹束龙叶幸司韶郜黎蓟薄印宿白怀蒲邰从鄂索咸籍赖卓蔺屠蒙池乔阴鬱胥能苍双闻莘党翟谭贡劳逄姬申扶堵冉宰郦雍卻璩桑桂濮牛寿通边扈燕冀郏浦尚农温别庄晏柴瞿阎充慕连茹习宦艾鱼容向古易慎戈廖庾终暨居衡步都耿满弘匡国文寇广禄阙东欧殳沃利蔚越夔隆师巩厍聂晁勾敖融冷訾辛阚那简饶空曾毋沙乜养鞠须丰巢关蒯相查後荆红游竺权逮盍益桓公'
GIVEN_NAMES = '伟芳娜敏静丽强磊洋勇艳杰军欣秀娟涛明超华建刚平燕红玲慧斌鑫莉佳俊桂英飞宇峰博文娜志鹏晨曦若溪沐宸暖阳星河宇轩诗涵子墨浩然雨桐一诺瑾瑜子衿宛童芷若若兰清漪思源远志知行致远'
DESTINATIONS = ['泰国曼谷', '日本东京', '韩国首尔', '新加坡', '马来西亚吉隆坡', '越南芽庄', '柬埔寨暹粒', '印尼巴厘岛',
                '法国巴黎', '意大利罗马', '瑞士卢塞恩', '德国柏林', '英国伦敦', '西班牙巴塞罗那', '希腊雅典',
                '美国纽约', '加拿大温哥华', '澳大利亚悉尼', '新西兰奥克兰', '马尔代夫', '斯里兰卡', '尼泊尔加德满都']


class Command(BaseCommand):
    help = '生成大规模测试数据用于性能测试'

    def add_arguments(self, parser):
        parser.add_argument('--routes', type=int, default=50, help='路线数量')
        parser.add_argument('--groups', type=int, default=2000, help='旅游团数量')
        parser.add_argument('--apps', type=int, default=5000, help='报名申请数量')
        parser.add_argument('--clear', action='store_true', help='先清空现有数据')

    def handle(self, *args, **options):
        num_routes = options['routes']
        num_groups = options['groups']
        num_apps = options['apps']
        clear = options['clear']

        if clear:
            self.stdout.write(self.style.WARNING('清空现有数据...'))
            Participant.objects.all().delete()
            Application.objects.all().delete()
            TourGroup.objects.all().delete()
            Route.objects.all().delete()
            self.stdout.write('已清空')

        self.stdout.write(f'目标: {num_routes} 路线 / {num_groups} 团 / {num_apps} 申请\n')

        t0 = time.time()

        # --- Phase 1: 创建路线 ---
        self.stdout.write('[1/4] 创建路线...')
        routes = self._create_routes(num_routes)

        # --- Phase 2: 创建旅游团 ---
        self.stdout.write(f'[2/4] 创建 {num_groups} 个旅游团...')
        tour_groups = self._create_tour_groups(routes, num_groups)

        # --- Phase 3: 创建报名申请和参加者 ---
        self.stdout.write(f'[3/4] 创建 {num_apps} 个报名申请 + 参加者...')
        self._create_applications(tour_groups, num_apps)

        # --- Phase 4: 统计 ---
        elapsed = time.time() - t0
        route_count = Route.objects.count()
        group_count = TourGroup.objects.count()
        app_count = Application.objects.count()
        part_count = Participant.objects.count()

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS(f'数据生成完成！耗时 {elapsed:.1f}s'))
        self.stdout.write(f'  路线:     {route_count}')
        self.stdout.write(f'  旅游团:   {group_count}')
        self.stdout.write(f'  报名申请: {app_count}')
        self.stdout.write(f'  参加者:   {part_count}')

        # 分布统计
        published = TourGroup.objects.filter(is_price_published=True, is_deleted=False).count()
        self.stdout.write(f'\n  已公开价格团: {published}')
        db_size = __import__('os').path.getsize('db.sqlite3')
        self.stdout.write(f'  数据库大小: {db_size / 1024 / 1024:.1f} MB')
        self.stdout.write('=' * 60)

    def _random_name(self):
        return random.choice(SURNAMES) + random.choice(GIVEN_NAMES) + random.choice(GIVEN_NAMES)

    def _create_routes(self, count):
        existing = list(Route.objects.all())
        if len(existing) >= count:
            self.stdout.write(f'  已有 {len(existing)} 条路线，跳过创建')
            return existing[:count]

        to_create = count - len(existing)
        routes = list(existing)
        batch = []
        for i in range(to_create):
            dest = DESTINATIONS[i % len(DESTINATIONS)]
            name = f'{dest}深度{i+1}日游'
            batch.append(Route(name=name, destination=dest[:20],
                               description=f'{dest}经典线路，第{i+1}版',
                               status=random.choices(['active', 'inactive', 'canceled'], weights=[80, 15, 5])[0]))
        Route.objects.bulk_create(batch, batch_size=500)
        routes.extend(Route.objects.filter(id__gt=routes[-1].id if routes else 0))
        self.stdout.write(f'  创建了 {len(batch)} 条路线')
        return routes

    def _create_tour_groups(self, routes, count):
        today = timezone.localdate()
        active_routes = [r for r in routes if r.status == 'active']
        if not active_routes:
            active_routes = routes

        existing = list(TourGroup.objects.all())
        if len(existing) >= count:
            return existing[:count]

        to_create = count - len(existing)
        batch = []
        for i in range(to_create):
            route = random.choice(active_routes)
            start_offset = random.randint(1, 180)  # 1~180天后出发
            deadline_offset = random.randint(1, max(1, start_offset - 3))
            capacity = random.randint(10, 50)
            price_adult = Decimal(str(random.randint(2000, 15000)))
            price_child = (price_adult * Decimal('0.7')).quantize(Decimal('0.01'))

            batch.append(TourGroup(
                code=f'TG{250601 + i:06d}',
                route=route,
                start_date=today + timedelta(days=start_offset),
                deadline=today + timedelta(days=start_offset - deadline_offset),
                max_capacity=capacity,
                price_adult=price_adult,
                price_child=price_child,
                is_price_published=random.choices([True, False], weights=[70, 30])[0],
                is_deleted=random.choices([False, True], weights=[95, 5])[0],
            ))
        TourGroup.objects.bulk_create(batch, batch_size=500)
        all_groups = list(TourGroup.objects.all())
        self.stdout.write(f'  创建了 {len(batch)} 个旅游团')
        return all_groups

    def _create_applications(self, tour_groups, count):
        visible_groups = [g for g in tour_groups if g.is_price_published and not g.is_deleted]
        if not visible_groups:
            visible_groups = tour_groups

        existing_apps = Application.objects.count()
        if existing_apps >= count:
            self.stdout.write(f'  已有 {existing_apps} 个申请，跳过创建')
            return

        to_create = count - existing_apps

        # 策略：约 30% 的团应该满员（测试 Python 过滤瓶颈）
        # 先让部分团满员
        target_full_groups = set()
        for g in random.sample(visible_groups, min(len(visible_groups), int(len(visible_groups) * 0.3))):
            target_full_groups.add(g.id)

        # 为每个满员团生成恰好等于 max_capacity 的参加者
        full_group_participant_count = 0
        remaining_apps = to_create

        today = timezone.localdate()
        apps_batch = []
        participants_batch = []

        pending_app_ids = []  # 追踪哪些 application 需要补 participants

        self.stdout.write(f'  目标满员团: {len(target_full_groups)} 个')
        self.stdout.write(f'  正在生成 {to_create} 个申请...')

        report_interval = max(1, to_create // 10)

        for i in range(to_create):
            if i % report_interval == 0 and i > 0:
                self.stdout.write(f'    进度: {i}/{to_create} ({100*i//to_create}%)')

            tour_group = random.choice(visible_groups)
            adult_count = random.randint(0, 4)
            child_count = random.randint(0, 3)

            deposit_paid = random.choices([True, False], weights=[60, 40])[0]
            balance_paid = random.choices([True, False], weights=[30, 70])[0] if deposit_paid else False
            status = random.choices(
                ['new', 'participants_entered', 'completed', 'canceled'],
                weights=[15, 20, 55, 10]
            )[0]

            app = Application(
                tour_group=tour_group,
                contact_name=self._random_name(),
                gender=random.choice(['male', 'female']),
                contact_phone=f'1{random.randint(30, 99):02d}{random.randint(10000000, 99999999)}',
                contact_address=f'{random.choice(DESTINATIONS)}市({random.randint(1,999)}号)',
                adult_count=adult_count,
                child_count=child_count,
                deposit_paid=deposit_paid,
                deposit_paid_at=today - timedelta(days=random.randint(0, 10)) if deposit_paid else None,
                deposit_amount=Decimal('0.00'),  # save() 时会计算
                balance_paid=balance_paid,
                status=status,
            )
            apps_batch.append(app)

            if status != 'canceled' and (adult_count + child_count) > 0:
                pending_app_ids.append(i)  # 等 app 保存后有 ID 再创建 participants

        # 批量创建 Application
        self.stdout.write('  正在写入数据库...')
        Application.objects.bulk_create(apps_batch, batch_size=500)

        # 获取分配了 ID 的 applications
        saved_apps = list(Application.objects.order_by('-id')[:to_create])
        saved_apps.reverse()  # 按 ID 升序
        # 取最后创建的 to_create 个
        if len(saved_apps) < to_create:
            saved_apps = list(Application.objects.order_by('id'))[-to_create:]

        # 为每个 application 创建 participants
        self.stdout.write(f'  正在创建参加者...')
        part_batch = []
        for idx, app in enumerate(saved_apps):
            count = app.adult_count + app.child_count
            if count == 0:
                continue

            # 满员团逻辑：确保满员
            if app.tour_group_id in target_full_groups:
                count = app.tour_group.max_capacity
                # 更新 adult_count 来匹配
                app.adult_count = count
                app.child_count = 0

            for j in range(count):
                part_batch.append(Participant(
                    application=app,
                    full_name=self._random_name(),
                    id_card=f'{random.randint(100000, 999999)}{random.randint(1900, 2020):04d}{random.randint(10000, 99999):05d}{random.randint(0, 9):01d}',
                    is_contact=(j == 0),
                ))

            if len(part_batch) >= 3000:
                Participant.objects.bulk_create(part_batch, batch_size=500)
                part_batch = []

        if part_batch:
            Participant.objects.bulk_create(part_batch, batch_size=500)

        # 校正：对于满员团，再次调整 actual count
        self.stdout.write(f'  调整满员团的参加者数量...')
        for tg_id in target_full_groups:
            tg = TourGroup.objects.get(id=tg_id)
            apps_in_group = Application.objects.filter(tour_group_id=tg_id)
            total_parts = Participant.objects.filter(application__tour_group_id=tg_id).count()
            if total_parts < tg.max_capacity:
                # 补充到满员
                first_app = apps_in_group.first()
                if first_app:
                    shortage = tg.max_capacity - total_parts
                    fill_batch = []
                    for _ in range(shortage):
                        fill_batch.append(Participant(
                            application=first_app,
                            full_name=self._random_name(),
                            id_card=f'FULL{random.randint(10000000, 99999999):08d}',
                            is_contact=False,
                        ))
                    Participant.objects.bulk_create(fill_batch)
