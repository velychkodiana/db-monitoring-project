from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
import sqlite3
import datetime

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "super-secret-key"  # Замінити у продакшн
jwt = JWTManager(app)

# --- Ініціалізація БД ---
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )""")
    conn.commit()
    conn.close()

init_db()

# --- Реєстрація ---
@app.post("/register")
def register():
    data = request.json
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                       (data["username"], data["password"]))
        conn.commit()
        return jsonify({"msg": "User created"}), 201
    except:
        return jsonify({"msg": "User already exists"}), 400
    finally:
        conn.close()

# --- Логін ---
@app.post("/login")
def login():
    data = request.json
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?",
                   (data["username"], data["password"]))
    user = cursor.fetchone()
    conn.close()

    if user:
        token = create_access_token(identity=data["username"], expires_delta=datetime.timedelta(hours=1))
        return jsonify(access_token=token)
    else:
        return jsonify({"msg": "Invalid credentials"}), 401

# --- Закрита зона ---
@app.get("/secure-data")
@jwt_required()
def secure_data():
    return jsonify({"data": "This is protected info."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005)
