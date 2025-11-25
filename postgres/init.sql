CREATE TABLE IF NOT EXISTS operations (
    id SERIAL PRIMARY KEY,
    operation_name TEXT NOT NULL,
    duration_ms INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

