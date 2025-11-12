#створюємо користувачів і робить логіни паралельно
import requests
import threading
import time
import argparse
import random

def register_user(base_url, username, password):
    try:
        r = requests.post(f"{base_url}/register", json={"username": username, "password": password}, timeout=5)
        return r.status_code, r.text
    except Exception as e:
        return None, str(e)

def login_user(base_url, username, password):
    try:
        r = requests.post(f"{base_url}/login", json={"username": username, "password": password}, timeout=5)
        return r.status_code, r.text
    except Exception as e:
        return None, str(e)

def worker_logins(base_url, usernames, password, stop_event, delay_min, delay_max):
    while not stop_event.is_set():
        u = random.choice(usernames)
        status, text = login_user(base_url, u, password)
        # optional: print(status, u)
        time.sleep(random.uniform(delay_min, delay_max))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--auth-url", default="http://localhost:5005", help="auth service base url")
    parser.add_argument("--users", type=int, default=100, help="how many users to register")
    parser.add_argument("--threads", type=int, default=10, help="how many concurrent login threads")
    parser.add_argument("--duration", type=int, default=60, help="duration in seconds to run logins")
    parser.add_argument("--password", default="pass", help="password for all users")
    parser.add_argument("--delay-min", type=float, default=0.5)
    parser.add_argument("--delay-max", type=float, default=2.0)
    args = parser.parse_args()

    base = args.auth_url.rstrip("/")

    # 1) Create users
    usernames = []
    for i in range(args.users):
        uname = f"user_{int(time.time())}_{i}"
        status, text = register_user(base, uname, args.password)
        if status == 201 or (status == 400 and "UNIQUE" in text.upper()):
            usernames.append(uname)
        else:
            # still append — even if it fails, we'll attempt logins
            usernames.append(uname)
        time.sleep(0.02)  # small gap to avoid hammering

    print(f"Registered/attempted {len(usernames)} users")

    # 2) Start login threads
    stop_event = threading.Event()
    threads = []
    for _ in range(args.threads):
        t = threading.Thread(target=worker_logins, args=(base, usernames, args.password, stop_event, args.delay_min, args.delay_max))
        t.daemon = True
        t.start()
        threads.append(t)

    print(f"Started {len(threads)} login threads for {args.duration} seconds")
    time.sleep(args.duration)
    stop_event.set()
    for t in threads:
        t.join(timeout=1)

    print("Traffic simulator finished")

if __name__ == "__main__":
    main()
