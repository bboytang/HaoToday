#!/usr/bin/env bash
# 在邀请内测期间创建普通个人账号。不产生管理员权限，不修改现有账号。
# 输入前须由运营方核对该内测者邮箱归属；此命令不会自动发验证邮件。
set -eu
cd /opt/haotoday
docker compose exec app python manage.py shell -v0 -c '
from getpass import getpass
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from django.db import transaction
email=input("内测账号邮箱：").strip().lower()
validate_email(email)
if len(email)>150 or get_user_model().objects.filter(username=email).exists():
    raise SystemExit("邮箱过长或账号已存在，未修改")
password=getpass("设置个人密码（输入不显示）：")
if password!=getpass("再次输入个人密码："):
    raise SystemExit("输入不一致，未创建")
u=get_user_model()(username=email,email=email)
validate_password(password,u)
with transaction.atomic():
    u.set_password(password)
    u.save(force_insert=True)
print("普通内测账号已创建。请在网站“我的”登录。")
'
