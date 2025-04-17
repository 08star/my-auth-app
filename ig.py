#!/usr/bin/env python3
# ig.py — 前端脚本（“前台”）

import argparse
import sys
import requests
from selenium import webdriver
# … 你原本的其他 import …

def authenticate(api_url, username, password):
    """向后端 /api/login 发送用户名/密码，返回 True/False"""
    resp = requests.post(
        f"{api_url}/api/login",
        json={"username": username, "password": password},
        timeout=10
    )
    if resp.status_code == 200 and resp.json().get("ok"):
        print("✅ 后台认证通过")
        return True
    else:
        print("❌ 后台认证失败:", resp.text)
        return False

def validate_device(api_url, username, device_id):
    """向后端 /api/validate_device 校验设备授权"""
    resp = requests.post(
        f"{api_url}/api/validate_device",
        json={"username": username, "device_id": device_id},
        timeout=10
    )
    if resp.status_code == 200 and resp.json().get("ok"):
        print("✅ 设备授权通过")
        return True
    else:
        print("❌ 设备未授权:", resp.text)
        return False

def parse_args():
    p = argparse.ArgumentParser(description="IG 自动化脚本（前台），先校验用户/设备。")
    p.add_argument("--api-url",    required=True,
                   help="管理端 API 根地址，例如 https://q8887.com")
    p.add_argument("--username",   required=True, help="管理端用户名")
    p.add_argument("--password",   required=True, help="管理端密码")
    p.add_argument("--device-id",  required=True, help="本机设备 ID")
    # … 如果你有更多选项可以继续加 …
    return p.parse_args()

def main():
    args = parse_args()

    # 第一步：登录认证
    if not authenticate(args.api_url, args.username, args.password):
        sys.exit(1)

    # 第二步：设备授权校验
    if not validate_device(args.api_url, args.username, args.device_id):
        sys.exit(1)

    # —— 上面两步通过后，才进入你原本的 IG 自动化逻辑 —— #
    # 下面举例如何启动 Selenium driver，并打开 Instagram
    options = webdriver.ChromeOptions()
    # … 你的 create_driver 逻辑 …
    driver = webdriver.Chrome(options=options)

    # 举例：登录、打开粉丝列表、follow_users…
    # from your_module import login_instagram, open_followers_list, follow_users
    if not login_instagram(driver, args.username, args.password, None):
        sys.exit(1)
    if not open_followers_list(driver, "some_target", None):
        sys.exit(1)
    follow_users(driver, max_follow=None, log_widget=None, stop_check=lambda: False)

if __name__ == "__main__":
    main()
