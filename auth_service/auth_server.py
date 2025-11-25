import os
import sqlite3
from flask import Flask, request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from prometheus_client import Counter, start_http_server

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

# -------- Prometheus metrics --------
auth_registered_users_total = Counter(
    "auth_registered_users_total", "Total number of registered users"
)
auth_login_attempts_total = Counter(
    "auth_login_attempts_total", "Total number of login attempts"
)
auth_successful_logins_total = Counter(
    "auth_successful_logins_total", "Total number of successful logins"
)

# -------- Flask app --------
app = Flask(__name__)


def get_db():
    """Return a SQLite connection bound to current request context."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create users table if it does not exist."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()
    conn.close()


@app.route("/")
def index():
    return jsonify({"status": "ok", "message": "Auth service is running"}), 200


# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    # Якщо просто відкриваєш в браузері - повертаємо просту HTML форму
    if request.method == "GET":
        return """
        <html>
        <body>
            <h2>Register</h2>
            <form method="post">
              <label>Username: <input name="username" /></label><br/>
              <label>Password: <input name="password" type="password" /></label><br/>
              <button type="submit">Register</button>
            </form>
        </body>
        </html>
        """

    # POST (з форми або JSON)
    data = request.form if request.form else request.json

    if not data:
        return jsonify({"error": "No data provided"}), 400

    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    db = get_db()
    cur = db.cursor()

    try:
        cur.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "User already exists"}), 409

    auth_registered_users_total.inc()

    return jsonify({"status": "ok", "message": "User registered"}), 201


# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    # GET — проста форма для ручної перевірки
    if request.method == "GET":
        return """
        <html>
        <body>
            <h2>Login</h2>
            <form method="post">
              <label>Username: <input name="username" /></label><br/>
              <label>Password: <input name="password" type="password" /></label><br/>
              <button type="submit">Login</button>
            </form>
        </body>
        </html>
        """

    auth_login_attempts_total.inc()

    data = request.form if request.form else request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
    row = cur.fetchone()

    if not row or not check_password_hash(row["password_hash"], password):
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401

    auth_successful_logins_total.inc()

    # Тут можна видати токен, але для проєкту достатньо просто OK
    return jsonify({"status": "ok", "message": "Login successful"}), 200


def main():
    # БД та таблиця
    init_db()

    # Запускаємо окремий HTTP сервер для метрик на порту 9200
    start_http_server(9200)

    # Flask API на 5005 (доступний з docker-compose)
    app.run(host="0.0.0.0", port=5005)


if __name__ == "__main__":
    main()
