import sqlite3
import pandas as pd

conn = sqlite3.connect('auth_devices.db')
df = pd.read_sql_query(
    "SELECT id AS 編號, username AS 使用者名稱, is_active AS 啟用狀態 FROM users",
    conn
)
print(df.to_string(index=False))
conn.close()
