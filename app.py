
import os
import uuid
import time
from flask import Flask, request, jsonify, abort
from extensions import db
import models   # register models after db
from selenium import webdriver
from selenium.webdriver.common.by import By

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# store active Selenium sessions
sessions = {}

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "username and password required"}), 400

    session_id = str(uuid.uuid4())
    profile_dir = os.path.join("profiles", f"{username}_{session_id}")
    os.makedirs(profile_dir, exist_ok=True)

    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(3)
        driver.find_element(By.NAME, "username").send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(5)
    except Exception as e:
        if driver:
            driver.quit()
        return jsonify({"error": f"Login error: {e}"}), 500

    # store session
    sessions[session_id] = driver

    # determine if challenge required
    if "challenge" in driver.current_url:
        return jsonify({"session_id": session_id, "challenge": True}), 202
    else:
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
        if code:
            inp = driver.find_element(By.NAME, "security_code")
            inp.send_keys(code)
            driver.find_element(By.XPATH, "//button").click()
        else:
            btn = driver.find_element(By.XPATH, "//button[contains(text(),'This Was Me') or contains(text(),'這是我')]")
            btn.click()
        time.sleep(5)
    except Exception as e:
        return jsonify({"error": f"Verify error: {e}"}), 500

    # check post-verification URL
    if "challenge" in driver.current_url:
        return jsonify({"verified": False}), 401
    return jsonify({"verified": True}), 200

if __name__ == "__main__":
    os.makedirs("profiles", exist_ok=True)
    app.run(host="0.0.0.0", port=int(os.getenv('PORT', 8000)))
```
