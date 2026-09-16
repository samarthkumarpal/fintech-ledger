import os
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ledger_db")

def get_db():
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>FinTech Core Banking Ledger</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@1/css/pico.min.css">
    <style>
        body { padding: 2rem; max-width: 1000px; margin: auto; }
        .positive { color: #2ecc71; font-weight: bold; }
        .negative { color: #e74c3c; font-weight: bold; }
    </style>
</head>
<body>
    <h2>🏛️ Double-Entry Core Banking Ledger</h2>
    <p>Live PostgreSQL 16 engine enforcing ACID double-entry constraints and deadlock-free transfers.</p>
    
    <div class="grid">
        <article>
            <header><strong>Transfer Funds</strong></header>
            <form id="transferForm">
                <label>Sender Account
                    <select id="sender" required>
                        {% for acc in accounts %}
                            <option value="{{ acc.account_id }}">{{ acc.account_number }} ({{ acc.account_type }})</option>
                        {% endfor %}
                    </select>
                </label>
                <label>Receiver Account
                    <select id="receiver" required>
                        {% for acc in accounts %}
                            <option value="{{ acc.account_id }}">{{ acc.account_number }} ({{ acc.account_type }})</option>
                        {% endfor %}
                    </select>
                </label>
                <label>Amount ($)
                    <input type="number" id="amount" step="0.01" min="1" value="25.00" required>
                </label>
                <button type="submit">Execute Atomic Transfer</button>
            </form>
            <p id="txResult"></p>
        </article>

        <article>
            <header><strong>Account Balances</strong></header>
            <table>
                <thead>
                    <tr><th>Account</th><th>Type</th><th>Balance</th></tr>
                </thead>
                <tbody>
                    {% for acc in balances %}
                    <tr>
                        <td><code>{{ acc.account_number }}</code></td>
                        <td>{{ acc.account_type }}</td>
                        <td><strong>${{ "%.2f"|format(acc.balance) }}</strong></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </article>
    </div>

    <article>
        <header><strong>Recent Ledger Entries (Audit Trail)</strong></header>
        <table>
            <thead>
                <tr><th>Time</th><th>Account</th><th>Amount</th><th>Type</th></tr>
            </thead>
            <tbody>
                {% for entry in entries %}
                <tr>
                    <td><small>{{ entry.created_at }}</small></td>
                    <td><code>{{ entry.account_number }}</code></td>
                    <td class="{{ 'positive' if entry.amount > 0 else 'negative' }}">${{ "%.2f"|format(entry.amount) }}</td>
                    <td>{{ entry.entry_type }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </article>

    <script>
        document.getElementById('transferForm').onsubmit = async (e) => {
            e.preventDefault();
            const res = await fetch('/transfer', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    sender_id: document.getElementById('sender').value,
                    receiver_id: document.getElementById('receiver').value,
                    amount: document.getElementById('amount').value
                })
            });
            const data = await res.json();
            const resElem = document.getElementById('txResult');
            if (res.ok) {
                resElem.innerHTML = `<span class="positive">Success! Tx ID: ${data.tx_id}</span>`;
                setTimeout(() => location.reload(), 1000);
            } else {
                resElem.innerHTML = `<span class="negative">Error: ${data.error}</span>`;
            }
        };
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT account_id, account_number, account_type FROM accounts ORDER BY account_number;")
    accounts = cur.fetchall()

    cur.execute("""
        SELECT a.account_number, a.account_type, COALESCE(SUM(l.amount), 0) as balance 
        FROM accounts a 
        LEFT JOIN ledger_entries l ON a.account_id = l.account_id 
        GROUP BY a.account_id, a.account_number, a.account_type 
        ORDER BY a.account_number;
    """)
    balances = cur.fetchall()

    cur.execute("""
        SELECT l.created_at, a.account_number, l.amount, l.entry_type 
        FROM ledger_entries l 
        JOIN accounts a ON l.account_id = a.account_id 
        ORDER BY l.created_at DESC LIMIT 15;
    """)
    entries = cur.fetchall()
    cur.close()
    conn.close()

    return render_template_string(HTML_TEMPLATE, accounts=accounts, balances=balances, entries=entries)

@app.route("/transfer", methods=["POST"])
def transfer():
    data = request.json
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT process_transfer(%s, %s, %s, %s);", 
                    (data["sender_id"], data["receiver_id"], float(data["amount"]), str(uuid.uuid4())))
        tx_id = cur.fetchone()["process_transfer"]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "success", "tx_id": tx_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))