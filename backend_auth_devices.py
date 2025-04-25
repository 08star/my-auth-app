import threading
import tkinter as tk
from tkinter import messagebox
import requests
import uuid

# 後端 API Base URL
API_BASE = "http://34.93.60.210:8000"

# 取得本機唯一裝置 ID（使用 MAC 地址）
DEVICE_ID = hex(uuid.getnode())

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Login & Device Authorization")
        self.geometry("320x300")

        # JWT Token
        self.token = None

        # Login Frame
        self.login_frame = tk.Frame(self)
        tk.Label(self.login_frame, text="Username:").grid(row=0, column=0, pady=5, sticky="e")
        self.username_var = tk.StringVar()
        tk.Entry(self.login_frame, textvariable=self.username_var).grid(row=0, column=1)
        tk.Label(self.login_frame, text="Password:").grid(row=1, column=0, pady=5, sticky="e")
        self.password_var = tk.StringVar()
        tk.Entry(self.login_frame, textvariable=self.password_var, show="*").grid(row=1, column=1)
        tk.Button(self.login_frame, text="Login", command=self.login).grid(row=2, columnspan=2, pady=10)
        self.login_frame.pack(pady=20)

        # Device Frame (login 後顯示)
        self.device_frame = tk.Frame(self)
        tk.Label(self.device_frame, text="Device ID:").grid(row=0, column=0, sticky="e")
        self.device_label = tk.Label(self.device_frame, text=DEVICE_ID)
        self.device_label.grid(row=0, column=1, sticky="w")
        self.status_label = tk.Label(self.device_frame, text="Status: unknown")
        self.status_label.grid(row=1, columnspan=2, pady=5)
        tk.Button(self.device_frame, text="Request Bind", command=self.register_device).grid(row=2, column=0, pady=5)
        tk.Button(self.device_frame, text="Refresh Status", command=self.check_device).grid(row=2, column=1, pady=5)
        self.proceed_btn = tk.Button(self.device_frame, text="Proceed to IG Bot", command=self.proceed)

        # 主要功能 Frame（綁定成功後顯示）
        self.main_frame = tk.Frame(self)
        tk.Label(self.main_frame, text="Device authorized! You can now use the IG bot.").pack(pady=20)

    def login(self):
        user = self.username_var.get().strip()
        pwd = self.password_var.get().strip()
        if not user or not pwd:
            messagebox.showwarning("Input Error", "Please enter username and password.")
            return
        threading.Thread(target=self._do_login, args=(user, pwd), daemon=True).start()

    def _do_login(self, user, pwd):
        try:
            r = requests.post(f"{API_BASE}/auth/login", json={"username": user, "password": pwd})
        except Exception as e:
            messagebox.showerror("Error", f"Login request failed: {e}")
            return

        # 處理非 200 回應
        if r.status_code != 200:
            text = r.text
            try:
                err = r.json().get("error", text)
            except ValueError:
                err = text
            messagebox.showerror("Login failed", f"Status {r.status_code}: {err}")
            return

        data = r.json()
        self.token = data.get("access_token")
        messagebox.showinfo("Login", "Login successful.")
        self.login_frame.pack_forget()
        self.device_frame.pack(pady=20)
        self.check_device()

    def register_device(self):
        if not self.token:
            return
        threading.Thread(target=self._do_register, daemon=True).start()

    def _do_register(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            r = requests.post(f"{API_BASE}/devices/register", json={"device_id": DEVICE_ID}, headers=headers)
        except Exception as e:
            messagebox.showerror("Error", f"Register device failed: {e}")
            return

        if r.status_code not in (200,201):
            try:
                err = r.json().get("error", r.text)
            except ValueError:
                err = r.text
            messagebox.showerror("Error", f"Status {r.status_code}: {err}")
            return

        data = r.json()
        verified = data.get("verified", False)
        self.status_label.config(text=f"Status: {'Verified' if verified else 'Unverified'}")
        if verified:
            self.show_proceed()
        else:
            messagebox.showinfo("Info", data.get("msg", "Device registration requested."))

    def check_device(self):
        threading.Thread(target=self._do_check, daemon=True).start()

    def _do_check(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            r = requests.get(f"{API_BASE}/devices", headers=headers)
        except Exception as e:
            messagebox.showerror("Error", f"Fetch devices failed: {e}")
            return

        if r.status_code != 200:
            messagebox.showerror("Error", f"Status {r.status_code}: {r.text}")
            return

        lst = r.json()
        for d in lst:
            if d['device_id'] == DEVICE_ID:
                verified = d['verified']
                self.status_label.config(text=f"Status: {'Verified' if verified else 'Unverified'}")
                if verified:
                    self.show_proceed()
                return
        self.status_label.config(text="Status: Not registered")

    def show_proceed(self):
        self.proceed_btn.grid(row=3, columnspan=2, pady=10)

    def proceed(self):
        messagebox.showinfo("Proceed", "Launching IG auto-follow...")
        # TODO: import 並呼叫你的 ig 自動追蹤模組

if __name__ == "__main__":
    app = App()
    app.mainloop()
