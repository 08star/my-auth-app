#!/usr/bin/env python3
# coding: utf-8

import os
import time
import random
import argparse

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 可选弹窗：仅在本地调试时生效
try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    tk = None
    messagebox = None

def create_driver(headless: bool, use_proxy: bool, session_id: str):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    # 以下若需代理，可自行在此处加入 proxy 相关配置
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation","enable-logging"])
    service = Service(ChromeDriverManager().install(), log_path="NUL")
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(10)
    return driver

def login_instagram(driver, username: str, password: str):
    print("🚀 前往 Instagram 登录页...")
    driver.get("https://www.instagram.com/accounts/login/")
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "username")))
    driver.find_element(By.NAME, "username").send_keys(username)
    driver.find_element(By.NAME, "password").send_keys(password + Keys.RETURN)

    # 自动跳转或手动验证
    try:
        WebDriverWait(driver, 10).until(lambda d: "/accounts/login" not in d.current_url)
    except:
        print("⚠️ 可能需要手动验证，请在浏览器完成后按回车继续。")
        if messagebox:
            messagebox.showinfo("验证", "请在浏览器完成验证后点击「确定」")
        else:
            input("完成验证后按回车继续…")

    print("✅ 登录成功！")
    time.sleep(random.uniform(3, 6))

def open_followers_list(driver, target: str):
    print(f"🚀 打开目标主页 {target} 的粉丝列表...")
    driver.get(f"https://www.instagram.com/{target}/")
    # 等待“followers”链接出现（中文界面可能是“粉丝”或“追随者”）
    WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "followers"))
    ).click()
    # 等待对话框弹出
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']"))
    )
    print("✅ 粉丝列表已打开")
    time.sleep(2)

def follow_users(driver, max_follow: int = None):
    print("🚀 开始追踪粉丝…")
    followed = 0
    # 记录上次滚动高度，用于检测是否到底部
    last_height = 0

    # 找到滚动容器
    dialog = driver.find_element(By.XPATH, "//div[@role='dialog']//div[@role='dialog']")
    while True:
        buttons = dialog.find_elements(By.XPATH,
            ".//button[.//div[text()='追蹤']]"  # 中文版按钮文字
        )
        for btn in buttons:
            if max_follow and followed >= max_follow:
                print("🎉 已达到最大追踪数，停止。")
                return
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                time.sleep(1)
                btn.click()
                followed += 1
                print(f"✅ 已追踪 ({followed})")
                time.sleep(random.uniform(4, 8))
            except Exception as e:
                print(f"❌ 追踪失败: {e}")
        # 滚动容器到底
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", dialog)
        time.sleep(random.uniform(2, 4))
        new_height = driver.execute_script("return arguments[0].scrollHeight;", dialog)
        if new_height == last_height:
            print("⏹️ 已到底部，结束追踪流程。")
            break
        last_height = new_height

    print("✅ 追踪流程结束")

def main():
    parser = argparse.ArgumentParser(description="Instagram Auto-Follow Bot")
    parser.add_argument("--username",   required=True, help="Instagram 帐号")
    parser.add_argument("--password",   required=True, help="Instagram 密码")
    parser.add_argument("--target",     required=True, help="目标主页用户名")
    parser.add_argument("--max-follow", type=int, default=None, help="最大追踪数量，不填则追到底")
    parser.add_argument("--headless",   action="store_true", help="启用无头模式")
    parser.add_argument("--no-proxy",   dest="use_proxy", action="store_false", help="禁用代理")
    args = parser.parse_args()

    driver = create_driver(headless=args.headless, use_proxy=args.use_proxy, session_id=args.username)
    try:
        login_instagram(driver, args.username, args.password)
        open_followers_list(driver, args.target)
        follow_users(driver, args.max_follow)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
