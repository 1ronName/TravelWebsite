# TravelWebsite — 旅行社管理系统

基于 Django 4.2 开发的旅游管理系统，支持旅游路线管理、团次发布、客户报名、财务对账等功能。

## 技术栈

- **Python 3**
- **Django 4.2.13**
- **SQLite**（文件数据库，无需额外配置）
- **openpyxl**（Excel 导出支持）

## 快速开始

### 1. 进入项目目录

```bash
cd TravelWebsite
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 数据库迁移

```bash
python manage.py migrate
```

### 4. 启动开发服务器

```bash
python manage.py runserver
```

默认访问地址：**http://127.0.0.1:8000/**

### 5. 填充演示数据（可选）

```bash
python manage.py populate_demo
```

### 6. 运行单元测试

```bash
python manage.py test tours applications users finance
```

项目已编写 **104 个单元测试**，全部通过。

## 项目结构

| 目录/文件 | 说明 |
|---|---|
| `manage.py` | Django 命令行入口 |
| `travel_agency/` | Django 项目配置（settings、urls、wsgi） |
| `tours/` | 旅游路线 & 团次管理 |
| `applications/` | 报名申请 & 参团管理 |
| `users/` | 用户权限 & 角色（路线管理员、前台、财务） |
| `finance/` | 财务对账 & CSV 导出 |
| `templates/` | HTML 模板 |
| `static/` | 静态文件（CSS） |

## 页面路由

| 路由 | 说明 |
|---|---|
| `/` | 旅游团列表 |
| `/applications/` | 报名申请 |
| `/finance/` | 财务接口 |
| `/admin/` | Django 后台管理 |

## 用户角色

| 角色 | 权限 |
|---|---|
| 路线管理员 (Route Manager) | 管理路线和团次 |
| 前台接待 (Front Desk) | 处理报名和参团 |
| 财务专员 (Finance Clerk) | 财务对账和导出 |

## 测试覆盖

| 模块 | 测试数 | 覆盖内容 |
|---|---|---|
| `tours/tests.py` | 30 | Route 模型、TourGroup 模型（含价格保护）、PriceChangeHistory、RouteChangeHistory、tour_list 视图 |
| `applications/tests.py` | 50 | Application 模型（总价/订金/退款计算）、Participant 模型（唯一约束）、表单验证、5 个视图 |
| `users/tests.py` | 16 | 权限装饰器（4 种角色）、post_migrate 信号 |
| `finance/tests.py` | 8 | CSV 导出视图（权限、格式、数据正确性、边界条件） |
