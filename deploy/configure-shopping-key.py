#!/usr/bin/env python3
"""只在运营方服务器交互终端写入购物源凭据；不联网、不改业务配置。"""
import getpass
import os
from pathlib import Path
import sys


def save_key(path, key):
    if not key or len(key)>512 or not key.isascii() or any(c.isspace() or ord(c)<33 or ord(c)==127 for c in key):
        raise ValueError("密钥格式无效，未保存")
    # 不覆盖现有凭据，也不创建额外明文备份。
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w") as out:
            out.write(key)
            out.flush()
            os.fsync(out.fileno())
    except BaseException:
        Path(path).unlink(missing_ok=True)
        raise


def main():
    if not sys.stdin.isatty():
        raise SystemExit("请在交互终端运行，不能通过管道传入密钥")
    path=Path("/opt/haotoday/.zhetaoke-key")
    if path.exists() or path.is_symlink():
        raise SystemExit("凭据文件已存在，未覆盖；如需轮换请先核对使用状态")
    key=getpass.getpass("输入本人折淘客 appkey（不显示）：")
    if key!=getpass.getpass("再次输入（不显示）："):
        raise SystemExit("两次不一致，未保存")
    try:
        save_key(path,key)
    except (ValueError,OSError):
        raise SystemExit("未能保存，请检查密钥格式、目录权限及是否已有文件")
    print("已保存至服务器私有文件，权限 0600。未调用接口，未开启采集。")


if __name__=="__main__":
    main()
