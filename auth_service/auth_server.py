from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
import sqlite3
from prometheus_client import start_http_server, Counter, Gauge
import time
import os

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "supersecret"
jwt = JWTManager(app)

# === Prometheus Metrics ===
login_attempts = Counter("auth_login_attempts_total", "Total login attempts")
successful_logins = Counter("auth_successful_logins_total", "Successful logins")
registered_users_gauge = Gauge("auth_registered_users_total", "Total number of registered users")

DB_PATH = "/app/users.db" if os.path.exists("/app") else "users.db"


# Create table if not exists
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()


def count_users():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    conn.close()
    return count


@app.before_request
def update_metrics():
    registered_users_gauge.set(count_users())



#   REGISTER USER

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "User already exists"}), 400

    conn.close()
    return jsonify({"message": "User registered"}), 201



# LOGIN
@app.route("/login", methods=["POST"])
def login():
    login_attempts.inc()

    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = cur.fetchone()
    conn.close()

    if user:
        successful_logins.inc()
        token = create_access_token(identity=username)
        return jsonify(access_token=token)

    return jsonify({"error": "Invalid credentials"}), 401


#  SECURE ENDPOINT

@app.route("/secure-data", methods=["GET"])
@jwt_required()
def secure():
    return jsonify({"data": "This is protected info."})


if __name__ == "__main__":
    # Prometheus metrics on port 9200
    start_http_server(9200)

    # Flask API on port 5005
    app.run(host="0.0.0.0", port=5005)
