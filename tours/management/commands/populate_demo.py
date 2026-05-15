from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from applications.models import Application, Participant
from tours.models import Route, TourGroup


class Command(BaseCommand):
    help = '为系统生成演示数据'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('开始生成演示数据...'))

        # 清理现有数据
        if self.ask_to_delete():
            # 按依赖顺序删除：Application -> Participant -> TourGroup -> Route
            Application.objects.all().delete()
            Participant.objects.all().delete()
            TourGroup.objects.all().delete()
            Route.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('已清理现有数据'))

        # 创建路线
        routes = self.create_routes()

        # 创建旅游团
        tour_groups = self.create_tour_groups(routes)

        # 创建申请单和参加者
        self.create_applications_and_participants(tour_groups)

        self.stdout.write(self.style.SUCCESS('演示数据生成完成！'))

    def ask_to_delete(self) -> bool:
        """询问是否删除现有数据"""
        response = input('是否删除现有数据？(y/n): ')
        return response.lower() == 'y'

    def create_routes(self) -> dict:
        """创建路线"""
        self.stdout.write('正在创建路线...')
        
        routes_data = [
            ('海南环岛游', '海南', '三亚、海口、蜈支洲岛等著名景点'),
            ('云南古镇游', '云南', '丽江、大理、古城等民族风情'),
            ('西藏朝圣游', '西藏', '拉萨、布达拉宫、羊湖等'),
            ('江南水乡游', '浙江', '杭州、乌镇、西塘等水乡古镇'),
        ]

        routes = {}
        for name, destination, description in routes_data:
            route, created = Route.objects.get_or_create(
                name=name,
                defaults={
                    'destination': destination,
                    'description': description,
                }
            )
            routes[name] = route
            if created:
                self.stdout.write(f'  ✓ 创建路线：{name}')
            else:
                self.stdout.write(f'  - 路线已存在：{name}')

        return routes

    def create_tour_groups(self, routes: dict) -> list:
        """创建旅游团"""
        self.stdout.write('正在创建旅游团...')

        today = timezone.localdate()
        tour_groups_data = [
            {
                'code': 'HN202605001',
                'route': '海南环岛游',
                'start_date': today + timedelta(days=15),  # 15天后出发
                'deadline': today + timedelta(days=10),
                'max_capacity': 20,
                'price_adult': Decimal('3500.00'),
                'price_child': Decimal('2500.00'),
                'is_price_published': True,  # 已公开价格，前台可见
            },
            {
                'code': 'YN202605001',
                'route': '云南古镇游',
                'start_date': today + timedelta(days=50),  # 50天后出发
                'deadline': today + timedelta(days=45),
                'max_capacity': 25,
                'price_adult': Decimal('4200.00'),
                'price_child': Decimal('3000.00'),
                'is_price_published': True,  # 已公开价格，前台可见
            },
            {
                'code': 'XZ202605001',
                'route': '西藏朝圣游',
                'start_date': today + timedelta(days=5),  # 5天后出发 - 近期
                'deadline': today + timedelta(days=2),
                'max_capacity': 15,
                'price_adult': Decimal('5800.00'),
                'price_child': Decimal('4500.00'),
                'is_price_published': False,  # 未公开价格，前台不可见
            },
            {
                'code': 'JN202605001',
                'route': '江南水乡游',
                'start_date': today + timedelta(days=90),  # 90天后出发 - 远期
                'deadline': today + timedelta(days=85),
                'max_capacity': 30,
                'price_adult': Decimal('2800.00'),
                'price_child': Decimal('2000.00'),
                'is_price_published': False,  # 未公开价格，前台不可见
            },
            {
                'code': 'HN202605002',
                'route': '海南环岛游',
                'start_date': today - timedelta(days=5),  # 已过期
                'deadline': today - timedelta(days=10),
                'max_capacity': 20,
                'price_adult': Decimal('3500.00'),
                'price_child': Decimal('2500.00'),
                'is_price_published': True,  # 即使公开也过期，前台不可见
            },
        ]

        tour_groups = []
        for data in tour_groups_data:
            route = routes[data.pop('route')]
            tour_group, created = TourGroup.objects.get_or_create(
                code=data['code'],
                defaults={**data, 'route': route}
            )
            tour_groups.append(tour_group)
            if created:
                self.stdout.write(f'  ✓ 创建旅游团：{data["code"]}（出发日期：{data["start_date"]}）')
            else:
                self.stdout.write(f'  - 旅游团已存在：{data["code"]}')

        return tour_groups

    def create_applications_and_participants(self, tour_groups: list):
        """创建申请单和参加者"""
        self.stdout.write('正在创建申请单和参加者...')

        today = timezone.localdate()

        applications_data = [
            {
                'tour_group': tour_groups[0],  # HN202605001 - 15天后
                'contact_name': '李明',
                'gender': 'male',
                'birth_date': '1985-06-15',
                'contact_phone': '13912345678',
                'contact_address': '北京市朝阳区',
                'email': 'liming@example.com',
                'postal_code': '100000',
                'emergency_contact_name': '李小红',
                'emergency_contact_relation': '妻子',
                'emergency_contact_phone': '13912345679',
                'emergency_contact_address': '北京市朝阳区',
                'adult_count': 2,
                'child_count': 1,
                'deposit_paid': True,
                'deposit_paid_at': today,
                'status': Application.Status.PARTICIPANTS_ENTERED,
                'participants': [
                    {'full_name': '李明', 'id_card': '110101198506151234', 'is_contact': True},
                    {'full_name': '李红', 'id_card': '110101198706201234', 'is_contact': False},
                    {'full_name': '李天', 'id_card': '110101201506251234', 'is_contact': False},
                ]
            },
            {
                'tour_group': tour_groups[1],  # YN202605001 - 50天后
                'contact_name': '王丽',
                'gender': 'female',
                'birth_date': '1990-03-20',
                'contact_phone': '13812345678',
                'contact_address': '上海市浦东新区',
                'email': 'wangli@example.com',
                'postal_code': '200000',
                'emergency_contact_name': '王敏',
                'emergency_contact_relation': '母亲',
                'emergency_contact_phone': '13812345680',
                'emergency_contact_address': '上海市浦东新区',
                'adult_count': 1,
                'child_count': 0,
                'deposit_paid': False,
                'status': Application.Status.NEW,
                'participants': []
            },
            {
                'tour_group': tour_groups[2],  # XZ202605001 - 5天后（近期）
                'contact_name': '张三',
                'gender': 'male',
                'birth_date': '1988-12-10',
                'contact_phone': '13712345678',
                'contact_address': '成都市武侯区',
                'email': 'zhangsan@example.com',
                'postal_code': '610000',
                'emergency_contact_name': '张四',
                'emergency_contact_relation': '兄弟',
                'emergency_contact_phone': '13712345681',
                'emergency_contact_address': '成都市武侯区',
                'adult_count': 3,
                'child_count': 0,
                'deposit_paid': True,
                'deposit_paid_at': today - timedelta(days=2),
                'status': Application.Status.COMPLETED,
                'participants': [
                    {'full_name': '张三', 'id_card': '510100198812101234', 'is_contact': True},
                    {'full_name': '张四', 'id_card': '510100198812101235', 'is_contact': False},
                    {'full_name': '张五', 'id_card': '510100199112201234', 'is_contact': False},
                ]
            },
            {
                'tour_group': tour_groups[3],  # JN202605001 - 90天后（远期）
                'contact_name': '周芳',
                'gender': 'female',
                'birth_date': '1995-07-08',
                'contact_phone': '13612345678',
                'contact_address': '杭州市西湖区',
                'email': 'zhoufang@example.com',
                'postal_code': '310000',
                'emergency_contact_name': '周林',
                'emergency_contact_relation': '父亲',
                'emergency_contact_phone': '13612345682',
                'emergency_contact_address': '杭州市西湖区',
                'adult_count': 2,
                'child_count': 2,
                'deposit_paid': False,
                'status': Application.Status.NEW,
                'participants': []
            },
        ]

        for app_data in applications_data:
            participants_data = app_data.pop('participants')
            app, created = Application.objects.get_or_create(
                tour_group=app_data['tour_group'],
                contact_phone=app_data['contact_phone'],
                defaults=app_data
            )
            
            if created:
                self.stdout.write(f'  ✓ 创建申请单：{app.contact_name}（团号：{app.tour_group.code}）')
                
                # 创建参加者
                for p_data in participants_data:
                    Participant.objects.create(application=app, **p_data)
                    self.stdout.write(f'    - 添加参加者：{p_data["full_name"]}')
            else:
                self.stdout.write(f'  - 申请单已存在：{app.contact_name}')
