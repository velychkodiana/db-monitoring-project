import time
import random
import psycopg2
from prometheus_client import start_http_server, Gauge, Counter, Histogram

# Метрики
operation_duration_metric = Gauge(
    "operation_duration_ms",
    "Duration of operations in milliseconds"
)

operations_total = Counter(
    "operations_total",
    "Total number of operations inserted into DB"
)

operation_duration_hist = Histogram(
    "operation_duration_hist_ms",
    "Histogram of operation duration",
    buckets=[10, 50, 100, 150, 200, 300, 500]
)

def main():
    conn = psycopg2.connect(
        dbname="test_db",
        user="test_user",
        password="test_password",
        host="postgres_db",
        port=5432
    )
    cursor = conn.cursor()

    while True:
        duration = random.randint(20, 400)

        cursor.execute(
            "INSERT INTO operations (operation_name, duration_ms) VALUES (%s, %s)",
            ("test_operation", duration)
        )
        conn.commit()

        # Оновлюємо всі метрики
        operations_total.inc()
        operation_duration_metric.set(duration)
        operation_duration_hist.observe(duration)

        print(f"Inserted operation: duration={duration} ms")

        time.sleep(1)

if __name__ == "__main__":
    start_http_server(9100)
    main()
