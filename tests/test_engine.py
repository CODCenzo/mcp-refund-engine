import json
import pytest
import sqlite3
from unittest.mock import patch
from src.server import get_transaction_and_policy

@pytest.fixture
def mock_db():
    """Sets up an in-memory database seeded with test data."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    # Recreate the schema in memory
    cursor.execute('''
        CREATE TABLE transactions (
            id TEXT PRIMARY KEY,
            amount INTEGER,
            created_at TEXT,
            status TEXT,
            merchant_id TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE policies (
            merchant_id TEXT PRIMARY KEY,
            max_refund_days INTEGER
        )
    ''')
    
    # Insert test seed data
    cursor.execute("INSERT INTO policies (merchant_id, max_refund_days) VALUES ('M-01', 30)")
    cursor.execute("INSERT INTO transactions (id, amount, created_at, status, merchant_id) VALUES ('TX-VALID', 5000, '2026-11-01', 'CAPTURED', 'M-01')")
    conn.commit()
    
    return conn

@patch('src.server.sqlite3.connect')
def test_get_transaction_and_policy_valid(mock_connect, mock_db):
    """Tests that a valid transaction returns the correct JOIN data."""
    # Force server.py to use our in-memory database instead of the real file
    mock_connect.return_value = mock_db
    
    result_json = get_transaction_and_policy("TX-VALID")
    result = json.loads(result_json)
    
    assert result["id"] == "TX-VALID"
    assert result["amount"] == 5000
    assert result["status"] == "CAPTURED"
    assert result["max_refund_days"] == 30

@patch('src.server.sqlite3.connect')
def test_get_transaction_and_policy_not_found(mock_connect, mock_db):
    """Tests the edge case for a non-existent transaction ID."""
    mock_connect.return_value = mock_db
    
    result_json = get_transaction_and_policy("TX-DOES-NOT-EXIST")
    result = json.loads(result_json)
    
    assert "error" in result
    assert result["error"] == "Transaction not found"