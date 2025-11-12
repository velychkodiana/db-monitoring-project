from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
import sqlite3
from prometheus_client import start_http_server, Counter, Gauge
import time

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "supersecret"
jwt = JWTManager(app)

# Prometheus Metrics
login_attempts = Counter("auth_login_attempts_total", "Total login attempts")
successful_logins = Counter("auth_successful_logins_total", "Successful logins")
registered_users_gauge = Gauge("auth_registered_users_total", "Total number of registered users")


def get_user_count():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    conn.close()
    return count


@app.before_request
def update_user_count_metric():
    registered_users_gauge.set(get_user_count())


@app.route("/login", methods=["POST"])
def login():
    login_attempts.inc()

    data = request.get_json()
    username = data["username"]
    password = data["password"]

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = cur.fetchone()
    conn.close()

    if user:
        successful_logins.inc()
        token = create_access_token(identity=username)
        return jsonify(access_token=token)

    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/secure-data", methods=["GET"])
@jwt_required()
def secure():
    return jsonify({"data": "This is protected info."})


if __name__ == "__main__":
    # Start Prometheus metrics endpoint on port 9200
    start_http_server(9200)
    app.run(host="0.0.0.0", port=5005)
