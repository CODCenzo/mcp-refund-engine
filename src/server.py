import sqlite3
import json
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("RefundEngine")

@mcp.tool()
def get_transaction_and_policy(transaction_id: str) -> str:
    """
    Fetches transaction details and the merchant's refund policy.
    The AI uses this tool to decide if a transaction is eligible for a refund.
    """
    conn = sqlite3.connect("refund_engine.db")
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()

    query = """
        SELECT t.id, t.amount, t.created_at, t.status, p.max_refund_days 
        FROM transactions t 
        JOIN policies p ON t.merchant_id = p.merchant_id
        WHERE t.id = ?
    """
    
    cursor.execute(query, (transaction_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return json.dumps(dict(row))
    else:
        return json.dumps({"error": "Transaction not found"})

if __name__ == "__main__":
    mcp.run(transport='stdio')