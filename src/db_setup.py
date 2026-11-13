import sqlite3
from datetime import date, timedelta

def setup_database():
    conn = sqlite3.connect("refund_engine.db")
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS transactions;")
    cursor.execute("DROP TABLE IF EXISTS policies;")

    cursor.execute("""
        CREATE TABLE policies (
            merchant_id TEXT PRIMARY KEY,
            max_refund_days INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE transactions (
            id TEXT PRIMARY KEY,
            amount INTEGER NOT NULL, -- Stored in cents (e.g., 5000 = $50.00)
            created_at DATE NOT NULL,
            status TEXT NOT NULL,
            merchant_id TEXT NOT NULL,
            FOREIGN KEY (merchant_id) REFERENCES policies (merchant_id)
        )
    """)

    cursor.execute("""
        INSERT INTO policies (merchant_id, max_refund_days)
        VALUES ('EBANX-DEMO', 30)
    """)

    today = date.today()
    date_5_days_ago = today - timedelta(days=5)
    date_45_days_ago = today - timedelta(days=45)

    # Insert mock transaction data
    transactions_data = [
        # TX-001: 5 days old, $50.00, should be ELIGIBLE for a refund
        ('TX-001', 5000, date_5_days_ago.isoformat(), 'CAPTURED', 'EBANX-DEMO'),
        
        # TX-002: 45 days old, $125.00, should be REJECTED (past 30 day policy)
        ('TX-002', 12500, date_45_days_ago.isoformat(), 'CAPTURED', 'EBANX-DEMO')
    ]

    cursor.executemany("""
        INSERT INTO transactions (id, amount, created_at, status, merchant_id)
        VALUES (?, ?, ?, ?, ?)
    """, transactions_data)

    conn.commit()
    conn.close()
    
    print("Database 'refund_engine.db' created and populated successfully!")

if __name__ == "__main__":
    setup_database()