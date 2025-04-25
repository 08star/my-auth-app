
import os
import uuid
import time
from flask import Flask, request, jsonify
from extensions import db
import models
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
sessions = {}

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json() or {}
    user = data.get("username")
    pwd = data.get("password")
    if not user or not pwd:
        return jsonify({"error": "username and password required"}), 400

    session_id = str(uuid.uuid4())
    prof = os.path.join("profiles", f"{user}_{session_id}")
    os.makedirs(prof, exist_ok=True)
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={prof}")
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get("https://www.instagram.com/accounts/login/")
        wait = WebDriverWait(driver, 15)
        # 等待 username 欄位可見
        user_field = wait.until(EC.visibility_of_element_located((By.NAME, "username")))
        pass_field = wait.until(EC.visibility_of_element_located((By.NAME, "password")))
        user_field.send_keys(user)
        pass_field.send_keys(pwd)
        login_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']")))
        login_btn.click()
        # 等待跳轉或挑戰頁
        time.sleep(5)
    except Exception as e:
        if driver:
            driver.quit()
        return jsonify({"error": f"Login error: {e}"}), 500

    sessions[session_id] = driver
    cur = driver.current_url
    if "challenge" in cur:
        return jsonify({"session_id": session_id, "challenge": True}), 202
    return jsonify({"session_id": session_id, "challenge": False}), 200

@app.route("/auth/verify", methods=["POST"])
def auth_verify():
    data = request.get_json() or {}
    sid = data.get("session_id")
    driver = sessions.get(sid)
    if not driver:
        return jsonify({"error": "invalid session_id"}), 400
    code = data.get("code")
    try:
        wait = WebDriverWait(driver, 15)
        if code:
            code_input = wait.until(EC.visibility_of_element_located((By.NAME, "security_code")))
            code_input.send_keys(code)
            code_input.submit()
        else:
            btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'This Was Me') or contains(text(),'這是我')]") ))
            btn.click()
        time.sleep(5)
    except Exception as e:
        return jsonify({"error": f"Verify error: {e}"}), 500

    if "challenge" in driver.current_url:
        return jsonify({"verified": False}), 401
    return jsonify({"verified": True}), 200

if __name__ == "__main__":
    os.makedirs("profiles", exist_ok=True)
    app.run(host="0.0.0.0", port=int(os.getenv('PORT', 8000)))

