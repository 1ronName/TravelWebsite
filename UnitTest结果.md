已为该项目编写了 104 个单元测试，覆盖 4 个模块，全部通过。同时发现并修复了 2 个应用代码 bug。

测试文件分布
文件	测试数	覆盖内容
tours/tests.py	30	Route 模型、TourGroup 模型（含价格保护逻辑）、PriceChangeHistory、RouteChangeHistory、tour_list 视图
applications/tests.py	50	Application 模型（总价/订金/退款计算、save 自动化）、Participant 模型（唯一约束）、表单验证、5 个视图
users/tests.py	16	权限装饰器（4种角色 × 多个场景）、post_migrate 信号
finance/tests.py	8	CSV 导出视图（权限、格式、数据正确性、边界条件）

测试架构

模型层测试 → 测试属性、方法、约束、save() 钩子
表单层测试 → 测试字段验证、必填项
视图层测试 → 使用 Django TestClient，测试权限控制、GET/POST 逻辑
信号测试   → 测试 post_migrate 自动建组

发现的 Bug 及修复
|Bug	|文件	|修复|
|---|---|---|
|cancel_fee_amount() 中 timezone.localtime()（datetime）与 DateField（date）类型不兼容	|applications/models.py:97	|改为 timezone.localdate()|
|save() 中余额自动计算存在循环依赖：balance_paid=True → balance_amount_due 返回 0 → 余额计算为 0	|applications/models.py:137	|直接计算 total_amount - deposit_amount|

运行测试
```Bash
cd TravelWebsite
python manage.py test tours applications users finance
```