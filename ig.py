import time
import random
import re
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import json
import os
import uuid
import zipfile

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager

# ========== Thordata 代理設定 ==========
# 代理用戶名結構：td-customer-[customerID]-sessid-[...]-sesstime-10
BRIGHTDATA_BASE_USER = "td-customer-jzQIlxh4eemb-country-kr"
BRIGHTDATA_PASS = "miOzQoye5a5b"  # 請確認密碼正確（全部小寫）
PROXY_HOST = "47ahfkuh.pr.thordata.net"
PROXY_PORT = 9999

# ========== 全域變數 ==========
accounts_file = "accounts.json"
accounts = []  # 帳號資料列表
driver_instances = {}  # 儲存各帳號的 WebDriver 物件，key 為 username
stop_flags = {}        # 儲存各帳號的停止旗標，key 為 username
account_cards = {}     # 儲存每個帳號的介面卡 (Text widget)，key 為 username
import sys, os
# 這會把所有 stderr 訊息都丟棄，包括真正的錯誤訊息也不會顯示！
sys.stderr = open(os.devnull, "w")
# ========== 存取帳號資料 ==========
def save_accounts():
    with open(accounts_file, 'w', encoding="utf-8") as f:
        json.dump(accounts, f, ensure_ascii=False, indent=2)

def load_accounts():
    if os.path.exists(accounts_file):
        with open(accounts_file, 'r', encoding="utf-8") as f:
            return json.load(f)
    return []

# ========== 代理認證擴充套件產生 ==========
def create_proxy_auth_extension(proxy_host, proxy_port, proxy_username, proxy_password, scheme='http', plugin_path='proxy_auth_plugin.zip'):
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Proxy Auth Extension",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version": "22.0.0"
    }
    """
    background_js = f"""
    var config = {{
        mode: "fixed_servers",
        rules: {{
            singleProxy: {{
                scheme: "{scheme}",
                host: "{proxy_host}",
                port: parseInt({proxy_port})
            }},
            bypassList: ["localhost"]
        }}
    }};
    chrome.proxy.settings.set({{value: config, scope: "regular"}}, function(){{}});

    function callbackFn(details) {{
        return {{
            authCredentials: {{
                username: "{proxy_username}",
                password: "{proxy_password}"
            }}
        }};
    }}

    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        {{urls: ["<all_urls>"]}},
        ["blocking"]
    );
    """
    with zipfile.ZipFile(plugin_path, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)
    return plugin_path
# ========== 限制日誌總量 ==========
def gui_log_local(log_widget, msg, max_lines=1000):
    log_widget.config(state=tk.NORMAL)
    log_widget.insert(tk.END, msg + "\n")
    # 檢查總行數是否超過 max_lines
    lines = log_widget.get("1.0", tk.END).splitlines()
    if len(lines) > max_lines:
        # 刪除最前面的 100 行（根據需要調整）
        log_widget.delete("1.0", "101.0")
    log_widget.see(tk.END)
    log_widget.config(state=tk.DISABLED)

# ========== 建立 WebDriver ==========
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def create_driver(session_id, headless=True, use_proxy=True):
    options = webdriver.ChromeOptions()
    
    # 如果需要無頭模式，使用 --headless（新版 chrome 推薦用 --headless=new）
    if headless:
        options.add_argument("--headless=new")  # 若新版請嘗試 "--headless=new"
    
    if use_proxy:
        # 使用代理：根據 session_id 組成代理用戶名並產生代理認證擴充套件
        proxy_username = f"{BRIGHTDATA_BASE_USER}-session-{session_id}"
        plugin_file = create_proxy_auth_extension(
            PROXY_HOST,
            PROXY_PORT,
            proxy_username,
            BRIGHTDATA_PASS,
            plugin_path=f"proxy_auth_{session_id}.zip"
        )
        options.add_extension(plugin_file)
    
    # 共用參數設定
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-insecure-localhost")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    # 以下參數用來減少不必要的 log 訊息
    options.add_argument("--silent")
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")  # 僅保留錯誤訊息
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # 也可以使用環境變數關閉 webdriver_manager 的 log（可選）
    os.environ["WDM_LOG_LEVEL"] = "0"
    
    # 將 ChromeDriver 日誌導向空檔（Windows 下使用 "NUL"，Linux/Mac 則使用 "/dev/null"）
    log_path = "NUL" if os.name == "nt" else "/dev/null"
    service = Service(ChromeDriverManager().install(), log_path=log_path)
    
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(10)
    return driver
# ========== 將日誌輸出到指定 widget ==========
def gui_log_local(log_widget, msg):
    log_widget.config(state=tk.NORMAL)
    log_widget.insert(tk.END, msg + "\n")
    log_widget.see(tk.END)
    log_widget.config(state=tk.DISABLED)
    log_widget.config(state=tk.DISABLED)

# ========== 解析粉絲數量 ==========
def parse_follower_count(text):
    t = text.replace(',', '').strip().lower()
    multiplier = 1
    if 'k' in t:
        t = t.replace('k', '')
        multiplier = 1000
    elif 'm' in t:
        t = t.replace('m', '')
        multiplier = 1000000
    elif '萬' in t:
        t = t.replace('萬', '')
        multiplier = 10000
    t = re.sub(r'[^\d\.]', '', t)
    try:
        return int(float(t) * multiplier)
    except:
        return None

# ========== 登入 Instagram ==========
def login_instagram(driver, username, password, log_widget):
    gui_log_local(log_widget, "🚀 前往 Instagram 登入頁...")
    driver.get("https://www.instagram.com")
    try:
        # 等待登入表單出現
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        # 輸入帳號與密碼並送出
        driver.find_element(By.NAME, "username").send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        
        # 根據 headless 模式決定等待自動跳轉方式
        if headless_var.get():
            WebDriverWait(driver, 10).until(lambda d: "login" not in d.current_url)
        else:
            try:
                WebDriverWait(driver, 10).until(lambda d: "login" not in d.current_url)
            except TimeoutException:
                current_url = driver.current_url
                if "challenge" in current_url or "checkpoint" in current_url:
                    gui_log_local(log_widget, "⚠️ 檢測到驗證挑戰，請在瀏覽器中完成手動驗證。")
                    messagebox.showinfo("手動驗證", "請在瀏覽器中完成驗證，完成後按下「確定」繼續。")
                    WebDriverWait(driver, 60).until(lambda d: "challenge" not in d.current_url and "checkpoint" not in d.current_url)
                else:
                    raise TimeoutException("自動跳轉超時且未偵測到驗證挑戰。")
        
        # 檢查是否出現密碼錯誤的錯誤提示元素，該元素的內容為：
        # <div class="xkmlbd1 xvs91rp xd4r4e8 x1anpbxc x1m39q7l xyorhqc x540dpk x2b8uid">很抱歉，你的密碼不正確，請再次檢查密碼。</div>
        try:
            error_element = driver.find_element(
                By.XPATH, 
                "//div[@class='xkmlbd1 xvs91rp xd4r4e8 x1anpbxc x1m39q7l xyorhqc x540dpk x2b8uid' and contains(text(), '很抱歉，你的密碼不正確，請再次檢查密碼。')]"
            )
            if error_element.is_displayed():
                raise Exception("登入失敗：密碼不正確")
        except NoSuchElementException:
            # 若找不到錯誤提示元素，則認為沒有密碼錯誤
            pass
        
        gui_log_local(log_widget, "✅ 登入成功！")
        time.sleep(random.uniform(5, 8))
        return True

    except Exception as e:
        gui_log_local(log_widget, f"❌ 登入失敗: {e}")
        messagebox.showinfo("登入失敗", "登入失敗，請檢查密碼，按 [確定] 停止運行。")
        return




# ========== 開啟粉絲列表 ==========
def open_followers_list(driver, target_profile, log_widget):
    gui_log_local(log_widget, f"🔎 前往 {target_profile} 的個人頁面...")
    time.sleep(random.uniform(2,5))
    driver.get(f"https://www.instagram.com/{target_profile}/")
    try:
        time.sleep(random.uniform(2,4))
        for _ in range(random.randint(1,3)):
            scroll_distance = random.randint(200,800)
            driver.execute_script("window.scrollBy(0, arguments[0]);", scroll_distance)
            time.sleep(random.uniform(1,2))
        followers_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/followers/')]"))
        )
        time.sleep(random.uniform(1,3))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", followers_button)
        time.sleep(random.uniform(1,3))
        followers_button.click()
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']"))
        )
        gui_log_local(log_widget, "✅ 成功開啟粉絲列表")
        return True
    except Exception as e:
        gui_log_local(log_widget, f"❌ 開啟粉絲列表失敗: {e}")
        return False

# ========== 取得粉絲總數 ==========
def get_followers_count(driver, log_widget):
    try:
        followers_element = driver.find_element(By.XPATH, "//ul/li[2]//a/span")
        followers_text = followers_element.get_attribute("title") or followers_element.text
        count = parse_follower_count(followers_text)
        if count is not None:
            gui_log_local(log_widget, f"🔎 目標帳號總粉絲數：{count}")
            return count
        else:
            gui_log_local(log_widget, f"❌ 無法解析粉絲數量：{followers_text}")
            return None
    except Exception as e:
        gui_log_local(log_widget, f"❌ 取得粉絲數量失敗: {e}")
        return None
# ========== 偵測封鎖彈窗 ==========
from selenium.common.exceptions import TimeoutException

def check_block_popup(driver, log_widget):
    try:
        # 選取所有 h1 或 h3 元素，若其文字中包含「稍後再試」或「暫時禁止」
        xpath_expr = "//*[self::h1 or self::h3][contains(text(), '稍後再試') or contains(text(), '暫時禁止')]"
        elements = driver.find_elements(By.XPATH, xpath_expr)
        for elem in elements:
            if elem.is_displayed():
                gui_log_local(log_widget, f"偵測到封鎖彈窗: {elem.text}")
                return True
    except Exception as e:
        gui_log_local(log_widget, f"檢查封鎖彈窗發生錯誤: {e}")
    return False



# ========== 追蹤流程 ==========
def follow_users(driver, max_follow, log_widget, stop_check):
    if stop_check():
        return
    gui_log_local(log_widget, "🚀 開始追蹤粉絲...")

    try:
        # 找到粉絲列表對話框
        followers_dialog = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@role='dialog']//div[contains(@class, 'x1ja2u2z')]")
            )
        )
        gui_log_local(log_widget, "✅ 成功找到粉絲列表對話框")
        try:
            # 搜尋所有已追蹤（狀態為“追蹤中”）的按鈕
            candidate_buttons = followers_dialog.find_elements(
                By.XPATH, "//button[.//div[contains(text(), '追蹤中')]]"
            )
            if candidate_buttons:
                # 隨機選取其中一個作為激活動作
                chosen_button = random.choice(candidate_buttons)
                time.sleep(2)
                chosen_button.click()
                time.sleep(2)
                gui_log_local(log_widget, "✅ 隨機點選已追蹤的按鈕以激活視窗")
                # 如果需要自動處理彈出的取消追蹤對話框，則加入下面邏輯：
                cancel_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'取消追蹤')]"))
                )
                cancel_btn.click()
            else:
                gui_log_local(log_widget, "❌ 找不到已追蹤的按鈕，可能沒有已追蹤的粉絲")
            # 等待一小段時間，讓激活操作生效
            time.sleep(2)
        except Exception as e:
            gui_log_local(log_widget, f"❌ 激活視窗按鈕處理失敗：{e}")
        
        # 檢查是否出現封鎖彈窗，如果有則暫停等待使用者介入
        if check_block_popup(driver, log_widget):
            gui_log_local(log_widget, "❌ 追蹤被限制，暫停中。")
            messagebox.showinfo("追蹤已被限制", "追蹤已被限制，按 [確定] 停止運行。")
            return

    except Exception as e:
        gui_log_local(log_widget, f"❌ 無法找到粉絲列表對話框: {e}")
        return

    total_followers = get_followers_count(driver, log_widget)
    followed_count = 0

    while not stop_check():
        follow_buttons = driver.find_elements(By.XPATH, "//button[.//div[contains(text(), '追蹤')]]")
        if not follow_buttons:
            gui_log_local(log_widget, "⏹️ 已到底部且沒有更多可追蹤的粉絲，請手動停止運行卡。")
            # 進入等待狀態，稍後會透過空白鍵捲動載入新的粉絲項目
            time.sleep(3)
            continue
        if total_followers is not None and followed_count >= total_followers:
            gui_log_local(log_widget, "🎉 已追蹤所有粉絲")
            break

        for button in follow_buttons:
            if stop_check():
                gui_log_local(log_widget, "🛑 停止追蹤")
                return
            try:
                btn_text = button.text.strip()
            except Exception:
                continue

            # 僅對按鈕文字完全為 "追蹤" 的進行點擊
            if btn_text == "追蹤":
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});",
                    button
                )
                time.sleep(1)
                try:
                    button.click()
                    followed_count += 1
                    gui_log_local(log_widget, f"✅ 追蹤成功 ({followed_count})")
                except Exception as e:
                    gui_log_local(log_widget, f"❌ 點擊追蹤按鈕失敗: {e}")
                    continue
                time.sleep(2)
                # 檢查封鎖彈窗，若出現則暫停流程，等待使用者介入
                if check_block_popup(driver, log_widget):
                    gui_log_local(log_widget, "❌ 追蹤被限制，暫停中。")
                    messagebox.showinfo("追蹤已被限制", "追蹤已被限制，按 [確定] 停止運行。")
                    return
                if max_follow and followed_count >= max_follow:
                    gui_log_local(log_widget, "🎉 達到設定的最大追蹤數量")
                    messagebox.showinfo("達到設定的最大追蹤數量", "已達到設定的最大追蹤數量，按 [確定] 停止追蹤。")
                    return
                time.sleep(random.uniform(5, 12))
            else:
                continue

        try:
            # 利用 body 元素發送空白鍵進行捲動，讓更多粉絲載入
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.SPACE)
            time.sleep(random.uniform(2, 5))
        except Exception as e:
            gui_log_local(log_widget, f"❌ 模擬空白鍵捲動失敗: {e}")
            break

    gui_log_local(log_widget, "✅ 追蹤流程結束")

# ========== 每個帳號運行時的卡片 ==========
def add_account_card(username):
    card = ttk.LabelFrame(cards_frame, text=username, padding="5")
    card.pack(fill="x", padx=5, pady=5)
    log_widget = tk.Text(card, height=10, state="disabled", wrap="word")
    log_widget.pack(side="left", fill="both", expand=True, padx=5, pady=5)
    sb = ttk.Scrollbar(card, orient="vertical", command=log_widget.yview)
    sb.pack(side="right", fill="y")
    log_widget.config(yscrollcommand=sb.set)
    # 儲存字典形式：同時存卡片與 log
    account_cards[username] = {"card": card, "log": log_widget}

# ========== 核心流程：每個帳號單獨運行 ==========
def run_account_task(account):
    username = account["username"]
    password = account["password"]
    target_profile = account.get("target", "")
    max_follow_str = account.get("max_follow", "")
    max_follow = int(max_follow_str) if max_follow_str.isdigit() else None

    # 固定 IP：使用帳號資料中的 session_id；若無則自動產生
    session_id = account.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())[:8]
        account["session_id"] = session_id

    # 先建立該帳號的運行卡
    add_account_card(username)
    card_widgets = account_cards.get(username)
    card_log_widget = card_widgets["log"] if card_widgets else None
    gui_log_local(card_log_widget, f"▶ {username} 使用代理 session: {session_id}")

    stop_flags[username] = False
    # 根據使用者選擇是否使用代理，將 use_proxy_var.get() 傳入 create_driver
    driver = create_driver(session_id, headless=headless_var.get(), use_proxy=use_proxy_var.get())
    driver_instances[username] = driver

    # 若使用代理，則檢查目前使用的 IP
    if use_proxy_var.get():
        check_proxy_ip(driver, card_log_widget)

    # 定義停止查詢 lambda
    def is_stopped(set_stop=False):
        if set_stop:
            stop_flags[username] = True
        return stop_flags.get(username, False)

    if not login_instagram(driver, username, password, card_log_widget):
        stop_following_account(username, card_widgets["card"] if card_widgets else None)
        return

    if not open_followers_list(driver, target_profile, card_log_widget):
        stop_following_account(username, card_widgets["card"] if card_widgets else None)
        return

    follow_users(driver, max_follow, card_log_widget, is_stopped)

    gui_log_local(card_log_widget, f"🚪 {username} 關閉瀏覽器並結束")
    try:
        driver.quit()
    except Exception as e:
        gui_log_local(card_log_widget, f"{username} 關閉瀏覽器時發生錯誤: {e}")
    driver_instances.pop(username, None)
    if card_widgets:
        card_widgets["card"].destroy()
        account_cards.pop(username, None)

def check_proxy_ip(driver, log_widget):
    try:
        # 透過代理開啟 ipify 網站
        driver.get("https://api.ipify.org")
        # 取得頁面內容（即當前使用的 IP）
        current_ip = driver.find_element(By.TAG_NAME, "body").text.strip()
        gui_log_local(log_widget, f"目前使用的IP地址：{current_ip}")
        return current_ip
    except Exception as e:
        gui_log_local(log_widget, f"檢查代理IP失敗：{e}")
        return None



# ========== 停止單一帳號 ==========
# 全域變數，記錄是否正在執行停止程序
stop_in_progress = {}

def stop_following_account(username, card_log_widget=None):
    # 如果停止程序已經在執行中，就不再重複執行
    if stop_in_progress.get(username, False):
        if card_log_widget:
            gui_log_local(card_log_widget, f"🛑 {username} 的停止程序正在執行，請稍候...")
        return

    stop_in_progress[username] = True  # 設定該帳號的停止程序正在執行

    try:
        stop_flags[username] = True  # 設定停止旗標

        # 如果有該帳號的 WebDriver 實例，嘗試關閉並移除它
        if username in driver_instances:
            try:
                driver_instances[username].quit()
            except Exception as e:
                if card_log_widget:
                    gui_log_local(card_log_widget, f"❌ 停止 {username} 任務時發生錯誤: {e}")
            finally:
                driver_instances.pop(username, None)
        
        # 記錄停止訊息
        if card_log_widget:
            gui_log_local(card_log_widget, f"🛑 {username} 任務已停止")
    finally:
        stop_in_progress[username] = False  # 清除該帳號的停止程序狀態


# ========== GUI 介面 ==========

root = tk.Tk()
root.title("IG 多帳號自動追蹤器")
root.geometry("650x900")

style = ttk.Style(root)
style.theme_use("clam")
style.configure("Green.TButton", foreground="white", background="#28a745",
                font=("Helvetica", 10, "bold"), padding=6)
style.map("Green.TButton", background=[("active", "#218838")])
style.configure("Red.TButton", foreground="white", background="#dc3545",
                font=("Helvetica", 10, "bold"), padding=6)
style.map("Red.TButton", background=[("active", "#c82333")])
style.configure("Grey.TButton", foreground="white", background="grey",
                font=("Helvetica", 10, "bold"), padding=6)
style.map("Grey.TButton", background=[("active", "dark grey")])

# 左側：帳號管理與新增
manage_frame = ttk.LabelFrame(root, text="帳號管理", padding="10")
manage_frame.pack(fill="x", padx=10, pady=10)

ttk.Label(manage_frame, text="Instagram 帳號:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
entry_username = ttk.Entry(manage_frame, width=30)
entry_username.grid(row=0, column=1, padx=5, pady=5)

ttk.Label(manage_frame, text="Instagram 密碼:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
entry_password = ttk.Entry(manage_frame, width=30, show="*")
entry_password.grid(row=1, column=1, padx=5, pady=5)

ttk.Label(manage_frame, text="目標帳號:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
entry_target = ttk.Entry(manage_frame, width=30)
entry_target.grid(row=2, column=1, padx=5, pady=5)

ttk.Label(manage_frame, text="最多追蹤人數 (留空=不限):").grid(row=3, column=0, sticky="w", padx=5, pady=5)
entry_max_follow = ttk.Entry(manage_frame, width=30)
entry_max_follow.grid(row=3, column=1, padx=5, pady=5)

ttk.Label(manage_frame, text="固定 Session ID (留空自動產生):").grid(row=4, column=0, sticky="w", padx=5, pady=5)
entry_session = ttk.Entry(manage_frame, width=30)
entry_session.grid(row=4, column=1, padx=5, pady=5)

ttk.Label(manage_frame, text="是否使用無頭模式:").grid(row=5, column=0, sticky="w", padx=5, pady=5)
headless_var = tk.BooleanVar(value=True)
chk_headless = ttk.Checkbutton(manage_frame, text="不顯示瀏覽器 (Headless)", variable=headless_var)
chk_headless.grid(row=5, column=1, sticky="w", padx=5, pady=5)

# 新增「是否使用代理」選項（放在 row 6）
ttk.Label(manage_frame, text="是否使用代理:").grid(row=6, column=0, sticky="w", padx=5, pady=5)
use_proxy_var = tk.BooleanVar(value=True)
chk_proxy = ttk.Checkbutton(manage_frame, text="使用代理", variable=use_proxy_var)
chk_proxy.grid(row=6, column=1, sticky="w", padx=5, pady=5)


def delete_account(username):
    # 在 accounts 中找出該帳號的索引
    idx = next((i for i, a in enumerate(accounts) if a["username"] == username), -1)
    if idx >= 0:
        # 從清單移除
        accounts.pop(idx)
        # 重新寫回 JSON 檔
        save_accounts()
        # 重新渲染帳號列表
        render_account_list()

def add_account_from_manage():
    new_acc = {
        "username": entry_username.get().strip(),
        "password": entry_password.get().strip(),
        "target": entry_target.get().strip(),
        "max_follow": entry_max_follow.get().strip(),
        "session_id": entry_session.get().strip() or str(uuid.uuid4())[:8]
    }
    if not new_acc["username"] or not new_acc["password"] or not new_acc["target"]:
        messagebox.showerror("錯誤", "請填寫完整的帳號、密碼與目標帳號")
        return
    accounts.append(new_acc)
    save_accounts()
    render_account_list()
    entry_username.delete(0, tk.END)
    entry_password.delete(0, tk.END)
    entry_target.delete(0, tk.END)
    entry_max_follow.delete(0, tk.END)
    entry_session.delete(0, tk.END)


# 移動新增按鈕到 row 7
btn_add = ttk.Button(manage_frame, text="新增帳號", command=add_account_from_manage, style="Green.TButton")
btn_add.grid(row=7, column=0, columnspan=2, pady=10)


# 帳號列表顯示區（包含啟動/停止/編輯按鈕）
list_frame = ttk.LabelFrame(root, text="帳號列表", padding="10")
list_frame.pack(fill="x", padx=10, pady=10)

def render_account_list():
    for widget in list_frame.winfo_children():
        widget.destroy()
    for acc in accounts:
        frame = ttk.Frame(list_frame, borderwidth=1, relief="solid", padding=5)
        frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(frame, text=f"帳號: {acc['username']}").pack(side="left", padx=5)
        ttk.Button(frame, text="編輯", command=lambda u=acc["username"]: edit_account(u)).pack(side="left", padx=5)
        ttk.Button(frame, text="啟動", command=lambda u=acc["username"]: start_account(u), style="Green.TButton").pack(side="left", padx=5)
        ttk.Button(frame, text="停止", command=lambda u=acc["username"]: stop_following_account(u, account_cards.get(u)["card"] if u in account_cards else None), style="Red.TButton").pack(side="left", padx=5)

        # ★ 新增「刪除」按鈕
        ttk.Button(frame, text="刪除", command=lambda u=acc["username"]: delete_account(u)).pack(side="left", padx=5)



accounts = load_accounts()
render_account_list()

# === 修改後：建立滾動容器 ===
# 建立一個容器 Frame 用於放置 Canvas 與 Scrollbar
cards_container = ttk.Frame(root)
cards_container.pack(fill="both", expand=True, padx=10, pady=10)

# 建立 Canvas（用於承載運行卡區）
cards_canvas = tk.Canvas(cards_container)
cards_canvas.pack(side="left", fill="both", expand=True)

# 建立垂直 Scrollbar 並與 Canvas 綁定
cards_scrollbar = ttk.Scrollbar(cards_container, orient="vertical", command=cards_canvas.yview)
cards_scrollbar.pack(side="right", fill="y")
cards_canvas.configure(yscrollcommand=cards_scrollbar.set)

# 建立內部 Frame 作為存放運行卡的區域，將其加入 Canvas
cards_frame = ttk.Frame(cards_canvas)
cards_canvas.create_window((0, 0), window=cards_frame, anchor="nw")

# 當 cards_frame 的尺寸改變時，更新 Canvas 的 scrollregion
def update_scrollregion(event):
    cards_canvas.configure(scrollregion=cards_canvas.bbox("all"))
cards_frame.bind("<Configure>", update_scrollregion)



def edit_account(username):
    account = next((a for a in accounts if a["username"] == username), None)
    if not account:
        return
    edit_win = tk.Toplevel(root)
    edit_win.title("編輯帳號")
    edit_win.grab_set()
    
    ttk.Label(edit_win, text="IG帳號:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
    ttk.Label(edit_win, text="密碼:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
    ttk.Label(edit_win, text="目標帳號:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
    ttk.Label(edit_win, text="最多追蹤人數:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
    ttk.Label(edit_win, text="固定 Session ID:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
    
    entry_edit_username = ttk.Entry(edit_win, width=30)
    entry_edit_username.grid(row=0, column=1, padx=5, pady=5)
    entry_edit_username.insert(0, account.get("username", ""))
    
    entry_edit_password = ttk.Entry(edit_win, width=30, show="*")
    entry_edit_password.grid(row=1, column=1, padx=5, pady=5)
    entry_edit_password.insert(0, account.get("password", ""))
    
    entry_edit_target = ttk.Entry(edit_win, width=30)
    entry_edit_target.grid(row=2, column=1, padx=5, pady=5)
    entry_edit_target.insert(0, account.get("target", ""))
    
    entry_edit_max_follow = ttk.Entry(edit_win, width=30)
    entry_edit_max_follow.grid(row=3, column=1, padx=5, pady=5)
    entry_edit_max_follow.insert(0, account.get("max_follow", ""))
    
    entry_edit_session = ttk.Entry(edit_win, width=30)
    entry_edit_session.grid(row=4, column=1, padx=5, pady=5)
    entry_edit_session.insert(0, account.get("session_id", ""))
    
    def save_changes():
        updated_username = entry_edit_username.get().strip()
        updated_password = entry_edit_password.get().strip()
        updated_target = entry_edit_target.get().strip()
        updated_max_follow = entry_edit_max_follow.get().strip()
        updated_session = entry_edit_session.get().strip()
        if not updated_username or not updated_password or not updated_target:
            messagebox.showerror("錯誤", "請填寫完整的帳號、密碼與目標帳號")
            return
        account["username"] = updated_username
        account["password"] = updated_password
        account["target"] = updated_target
        account["max_follow"] = updated_max_follow
        account["session_id"] = updated_session or str(uuid.uuid4())[:8]
        save_accounts()
        render_account_list()
        edit_win.destroy()
    
    ttk.Button(edit_win, text="儲存", command=save_changes).grid(row=5, column=0, columnspan=2, pady=10)
# ========== 從管理介面啟動帳號 ==========
# 全域變數，記錄各帳號的運行狀態，True 表示正在運行中
running_flags = {}

def start_account(username):
    # 如果該帳號已標記為運行中，就不再重複啟動
    if running_flags.get(username, False):
        messagebox.showinfo("已啟動", f"帳號 {username} 已經在運行中。")
        return

    running_flags[username] = True  # 設定為運行中

    # 取得該帳號的資料
    account = next((a for a in accounts if a["username"] == username), None)
    if not account:
        running_flags[username] = False  # 帳號不存在時重置狀態
        return

    # 若 session_id 尚未存在，則自動產生
    if "session_id" not in account or not account["session_id"]:
        account["session_id"] = str(uuid.uuid4())[:8]

    # 同時重置停止旗標（表示目前不在停止狀態）
    stop_flags[username] = False

    # 使用包裝函式啟動執行緒，執行完畢後記得重置 running_flags
    threading.Thread(target=run_account_task_wrapper, args=(account,), daemon=True).start()

def run_account_task_wrapper(account):
    try:
        run_account_task(account)
    finally:
        # 無論如何執行完畢後都將狀態重置
        running_flags[account["username"]] = False



import threading

def stop_following_account(username, card_widget=None):
    def background_stop():
        # 設定停止旗標
        stop_flags[username] = True
        
        # 嘗試關閉該帳號的 WebDriver
        if username in driver_instances:
            try:
                driver_instances[username].quit()
            except Exception as e:
                print(f"停止 {username} 時出錯：{e}")
        
        # 若有指定 card_widget，安排在主線程中銷毀，避免 UI 卡住
        if card_widget:
            def cleanup():
                card_widget.destroy()
                if username in account_cards:
                    account_cards.pop(username, None)
            card_widget.after(0, cleanup)
    
    # 將停止操作放到子執行緒中執行，避免阻塞 GUI 主線程
    threading.Thread(target=background_stop).start()


root.mainloop()
