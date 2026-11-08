import sqlite3
from datetime import datetime

DB_NAME = "cars.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            note TEXT DEFAULT '',
            vin TEXT DEFAULT '',
            category TEXT DEFAULT '',
            photo TEXT DEFAULT '',
            created_at TEXT DEFAULT ''
        )
    """)
    cur.execute("PRAGMA table_info(cars)")
    cols = [r[1] for r in cur.fetchall()]
    for col, default in [("note", "''"), ("vin", "''"), ("category", "''"), ("photo", "''"), ("created_at", "''")]:
        if col not in cols:
            cur.execute(f"ALTER TABLE cars ADD COLUMN {col} TEXT DEFAULT {default}")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_id INTEGER, action TEXT, details TEXT, timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_car(name, price, date, status, note="", vin="", category="", photo=""):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""INSERT INTO cars (name, price, date, status, note, vin, category, photo, created_at)
        VALUES (?,?,?,?,?,?,?,?,?)""", (name, price, date, status, note, vin, category, photo, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    car_id = cur.lastrowid
    conn.commit()
    conn.close()
    log_history(car_id, "Создано", f"{name} — {price} ₽")
    return car_id

def update_car(car_id, name, price, date, status, note="", vin="", category="", photo=""):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""UPDATE cars SET name=?, price=?, date=?, status=?, note=?, vin=?, category=?, photo=? WHERE id=?""",
        (name, price, date, status, note, vin, category, photo, car_id))
    conn.commit()
    conn.close()
    log_history(car_id, "Изменено", f"{name} — {status}")

def delete_car(car_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT name FROM cars WHERE id=?", (car_id,))
    row = cur.fetchone()
    name = row[0] if row else "?"
    cur.execute("DELETE FROM cars WHERE id=?", (car_id,))
    conn.commit()
    conn.close()
    log_history(car_id, "Удалено", name)

def get_car(car_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, name, price, date, status, note, vin, category, photo FROM cars WHERE id=?", (car_id,))
    row = cur.fetchone()
    conn.close()
    return row

def toggle_status(car_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT name, status FROM cars WHERE id=?", (car_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    name, status = row
    new_status = "Выполнено" if status == "В ожидании" else "В ожидании"
    cur.execute("UPDATE cars SET status=? WHERE id=?", (new_status, car_id))
    conn.commit()
    conn.close()
    log_history(car_id, "Статус", f"{status} → {new_status}")
    return new_status

def get_cars(search="", status="", category="", sort_by="new"):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    query = "SELECT id, name, price, date, status, note, vin, category, photo FROM cars WHERE 1=1"
    params = []
    if search:
        query += " AND (name LIKE ? OR vin LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    if status and status not in ("Все", "Все статусы"):
        query += " AND status = ?"
        params.append(status)
    if category and category not in ("Все", "Все категории"):
        query += " AND category = ?"
        params.append(category)
    sort_map = {
        "new": "ORDER BY id DESC", "old": "ORDER BY id ASC",
        "price_asc": "ORDER BY price ASC", "price_desc": "ORDER BY price DESC",
        "date_asc": "ORDER BY date ASC", "date_desc": "ORDER BY date DESC",
        "name_asc": "ORDER BY name COLLATE NOCASE ASC", "status": "ORDER BY status ASC, id DESC",
    }
    query += " " + sort_map.get(sort_by, "ORDER BY id DESC")
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_stats():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), SUM(price) FROM cars")
    total, total_sum = cur.fetchone()
    cur.execute("SELECT COUNT(*), SUM(price) FROM cars WHERE status='В ожидании'")
    pending, pending_sum = cur.fetchone()
    cur.execute("SELECT COUNT(*), SUM(price) FROM cars WHERE status='Выполнено'")
    done, done_sum = cur.fetchone()
    cur.execute("SELECT name, date FROM cars WHERE status='В ожидании' AND date >= date('now') ORDER BY date ASC LIMIT 1")
    nearest = cur.fetchone()
    conn.close()
    return {"total": total or 0, "total_sum": total_sum or 0, "pending": pending or 0, "pending_sum": pending_sum or 0, "done": done or 0, "done_sum": done_sum or 0, "nearest": nearest}

def get_categories():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT category FROM cars WHERE category != '' ORDER BY category")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows

def log_history(car_id, action, details):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT INTO history (car_id, action, details, timestamp) VALUES (?,?,?,?)", (car_id, action, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_history(car_id=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    if car_id:
        cur.execute("SELECT action, details, timestamp FROM history WHERE car_id=? ORDER BY id DESC", (car_id,))
    else:
        cur.execute("SELECT action, details, timestamp FROM history ORDER BY id DESC LIMIT 100")
    rows = cur.fetchall()
    conn.close()
    return rows
