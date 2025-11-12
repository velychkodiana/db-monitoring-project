import time
import random
import psycopg2
from prometheus_client import start_http_server, Gauge, Counter, Histogram

# Gauge: поточний час операції
operation_duration_metric = Gauge("operation_duration_ms", "Duration of operations in milliseconds")

# Counter: загальна кількість операцій
operations_total = Counter("operations_total", "Total number of operations inserted into DB")

# Histogram: розподіл тривалостей (для percentiles)
operation_duration_hist = Histogram("operation_duration_hist_ms", "Histogram of operation duration", buckets=[10,50,100,150,200,300,500,1000])

# Counter: помилки вставок
operation_errors = Counter("operation_insert_errors_total", "Total DB insert errors")

# Counter: по типах операцій (future extension)
operation_by_type = Counter("operation_by_type_total", "Number of operations by type", ['type'])

# DB-метрики
db_table_size = Gauge("db_table_size_bytes", "Size of operations table in bytes")
db_connections = Gauge("db_active_connections", "Number of active DB connections")

SLEEP_SECONDS = 1  # інтервал між вставками

def connect_with_retry():
    while True:
        try:
            conn = psycopg2.connect(
                dbname="test_db",
                user="test_user",
                password="test_password",
                host="postgres_db",
                port=5432
            )
            return conn
        except Exception as e:
            print("Postgres is not ready, retrying in 3 seconds...", e)
            time.sleep(3)

def main():
    conn = connect_with_retry()
    cursor = conn.cursor()

    while True:
        duration = random.randint(10, 400)
        op_type = "test_operation"  # можна варіювати, якщо потрібно

        try:
            cursor.execute(
                "INSERT INTO operations (operation_name, duration_ms) VALUES (%s, %s)",
                (op_type, duration)
            )
            conn.commit()

            # Метрики
            operations_total.inc()
            operation_duration_metric.set(duration)
            operation_duration_hist.observe(duration)
            operation_by_type.labels(type=op_type).inc()

            # DB size
            try:
                cursor.execute("SELECT pg_total_relation_size('operations');")
                size = cursor.fetchone()[0] or 0
                db_table_size.set(size)
            except Exception:
                db_table_size.set(0)

            # connections
            try:
                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE datname='test_db';")
                active_conn = cursor.fetchone()[0] or 0
                db_connections.set(active_conn)
            except Exception:
                db_connections.set(0)

            print(f"[OK] inserted duration={duration}ms, table_size={db_table_size._value.get() if hasattr(db_table_size,'_value') else 'n/a'}")
        except Exception as e:
            operation_errors.inc()
            print("Insert error:", e)
            # пробуємо знову підключитись при фатальній помилці
            conn = connect_with_retry()
            cursor = conn.cursor()

        time.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    start_http_server(9100)
    main()
