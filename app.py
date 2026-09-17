import os
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ledger_db")


def get_db():
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)


def fmt_money(value):
    """Render a signed amount with thousands separators, e.g. -1234.5 -> '-1,234.50'."""
    value = float(value)
    sign = "-" if value < 0 else ""
    return f"{sign}{abs(value):,.2f}"


PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ledger &mdash; Core Banking Console</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>&#128220;</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root{
    --bg:#0c1015;
    --panel:#11161d;
    --panel-2:#141a22;
    --border:#232b36;
    --border-soft:#1a2029;
    --text:#e6e9ee;
    --text-dim:#8b95a6;
    --text-faint:#5b6472;
    --credit:#3fb68b;
    --debit:#c9705f;
    --accent:#4f9ad1;
    --accent-dim:#2c5674;
    --radius:3px;
    --sans:'IBM Plex Sans', system-ui, sans-serif;
    --mono:'IBM Plex Mono', ui-monospace, 'SFMono-Regular', monospace;
  }
  *{box-sizing:border-box;}
  html,body{margin:0;padding:0;}
  body{
    background:var(--bg);
    color:var(--text);
    font-family:var(--sans);
    -webkit-font-smoothing:antialiased;
    line-height:1.5;
    padding:2.5rem 1.5rem 4rem;
  }
  .wrap{max-width:1080px;margin:0 auto;}

  .masthead{
    display:flex;
    justify-content:space-between;
    align-items:flex-end;
    flex-wrap:wrap;
    gap:1rem 2rem;
    border-bottom:1px solid var(--border);
    padding-bottom:1.5rem;
    margin-bottom:1.5rem;
  }
  .masthead h1{
    font-size:1.5rem;
    font-weight:600;
    letter-spacing:-0.01em;
    margin:0 0 0.3rem;
  }
  .masthead p{
    margin:0;
    color:var(--text-dim);
    font-size:0.9rem;
    max-width:46ch;
  }
  .stat-row{display:flex;gap:2rem;}
  .stat{text-align:right;}
  .stat .n{
    font-family:var(--mono);
    font-size:1.25rem;
    font-weight:600;
    font-variant-numeric:tabular-nums;
    display:block;
  }
  .stat .n.ok{color:var(--credit);}
  .stat .n.bad{color:var(--debit);}
  .stat .l{
    font-size:0.72rem;
    color:var(--text-faint);
    display:block;
    margin-top:0.15rem;
  }

  .grid{
    display:grid;
    grid-template-columns:1fr 1.3fr;
    gap:1.25rem;
    margin-bottom:1.25rem;
  }
  @media (max-width:760px){ .grid{grid-template-columns:1fr;} }

  .panel{
    background:var(--panel);
    border:1px solid var(--border);
    border-radius:var(--radius);
  }
  .panel-head{
    padding:0.85rem 1.1rem;
    border-bottom:1px solid var(--border);
    display:flex;
    justify-content:space-between;
    align-items:center;
  }
  .panel-head h2{
    font-size:0.82rem;
    font-weight:600;
    margin:0;
    color:var(--text);
  }
  .panel-head .hint{font-size:0.75rem;color:var(--text-faint);}
  .panel-body{padding:1.1rem;}

  label{
    display:block;
    font-size:0.78rem;
    color:var(--text-dim);
    margin-bottom:0.35rem;
  }
  .field{margin-bottom:1rem;}
  select,input{
    width:100%;
    background:var(--panel-2);
    border:1px solid var(--border);
    color:var(--text);
    padding:0.55rem 0.65rem;
    border-radius:var(--radius);
    font-family:var(--mono);
    font-size:0.9rem;
  }
  select:focus,input:focus,button:focus-visible{
    outline:2px solid var(--accent);
    outline-offset:1px;
    border-color:var(--accent);
  }
  .swap-row{
    display:flex;
    align-items:center;
    gap:0.6rem;
    margin:-0.4rem 0 1rem;
  }
  .swap-row button{
    all:unset;
    cursor:pointer;
    color:var(--text-faint);
    font-size:0.72rem;
    font-family:var(--mono);
    border:1px solid var(--border-soft);
    padding:0.2rem 0.5rem;
    border-radius:var(--radius);
  }
  .swap-row button:hover{color:var(--accent);border-color:var(--accent-dim);}

  button[type="submit"]{
    width:100%;
    background:var(--accent);
    color:#08121a;
    border:none;
    font-family:var(--sans);
    font-weight:600;
    font-size:0.88rem;
    padding:0.65rem;
    border-radius:var(--radius);
    cursor:pointer;
    transition:background .15s ease;
  }
  button[type="submit"]:hover{background:#69b0dd;}
  button[type="submit"]:disabled{background:var(--accent-dim);cursor:progress;}

  #txResult{
    margin-top:0.8rem;
    font-size:0.83rem;
    font-family:var(--mono);
    min-height:1.2em;
  }
  #txResult.ok{color:var(--credit);}
  #txResult.err{color:var(--debit);}

  table{width:100%;border-collapse:collapse;font-size:0.85rem;}
  th{
    text-align:left;
    font-size:0.72rem;
    color:var(--text-faint);
    font-weight:500;
    padding:0 0.5rem 0.5rem;
    border-bottom:1px solid var(--border);
  }
  td{
    padding:0.5rem;
    border-bottom:1px solid var(--border-soft);
    color:var(--text);
    vertical-align:middle;
  }
  tr:last-child td{border-bottom:none;}
  .num{
    font-family:var(--mono);
    text-align:right;
    font-variant-numeric:tabular-nums;
    white-space:nowrap;
  }
  .credit{color:var(--credit);}
  .debit{color:var(--debit);}
  .acct-code{font-family:var(--mono);font-size:0.83rem;}
  .type-tag{
    font-size:0.68rem;
    color:var(--text-faint);
    border:1px solid var(--border-soft);
    border-radius:var(--radius);
    padding:0.08rem 0.4rem;
    margin-left:0.5rem;
  }
  .ts{color:var(--text-faint);font-size:0.78rem;white-space:nowrap;}
  .scroll-x{overflow-x:auto;}
  .empty-row td{color:var(--text-faint);text-align:center;padding:1.5rem;}

  footer{
    margin-top:2rem;
    padding-top:1rem;
    border-top:1px solid var(--border);
    font-size:0.75rem;
    color:var(--text-faint);
    display:flex;
    justify-content:space-between;
    flex-wrap:wrap;
    gap:0.5rem;
  }
</style>
</head>
<body>
<div class="wrap">

  <header class="masthead">
    <div>
      <h1>Double-Entry Core Banking Ledger</h1>
      <p>PostgreSQL 16 engine. Every transfer posts a balanced debit/credit pair inside one transaction, with deterministic lock ordering to stay deadlock-free under concurrency.</p>
    </div>
    <div class="stat-row">
      <div class="stat">
        <span class="n {{ 'ok' if net_position == 0 else 'bad' }}">${{ net_fmt }}</span>
        <span class="l">net position</span>
      </div>
      <div class="stat">
        <span class="n">{{ account_count }}</span>
        <span class="l">accounts</span>
      </div>
      <div class="stat">
        <span class="n">{{ entry_count }}</span>
        <span class="l">ledger entries</span>
      </div>
    </div>
  </header>

  <div class="grid">
    <section class="panel">
      <div class="panel-head"><h2>Transfer funds</h2></div>
      <div class="panel-body">
        <form id="transferForm">
          <div class="field">
            <label for="sender">Sender account</label>
            <select id="sender" required>
              {% for acc in accounts %}
                <option value="{{ acc.account_id }}">{{ acc.account_number }} &middot; {{ acc.account_type }}</option>
              {% endfor %}
            </select>
          </div>

          <div class="swap-row">
            <button type="button" id="swapBtn" title="Swap sender and receiver">&#8645; swap</button>
          </div>

          <div class="field">
            <label for="receiver">Receiver account</label>
            <select id="receiver" required>
              {% for acc in accounts %}
                <option value="{{ acc.account_id }}" {{ 'selected' if loop.index0 == 1 else '' }}>{{ acc.account_number }} &middot; {{ acc.account_type }}</option>
              {% endfor %}
            </select>
          </div>

          <div class="field">
            <label for="amount">Amount (USD)</label>
            <input type="number" id="amount" step="0.01" min="0.01" value="25.00" required>
          </div>

          <button type="submit" id="submitBtn">Execute atomic transfer</button>
        </form>
        <p id="txResult"></p>
      </div>
    </section>

    <section class="panel">
      <div class="panel-head">
        <h2>Account balances</h2>
        <span class="hint">live</span>
      </div>
      <div class="panel-body scroll-x">
        <table>
          <thead>
            <tr><th>Account</th><th class="num">Balance</th></tr>
          </thead>
          <tbody>
            {% for acc in balances %}
            <tr>
              <td>
                <span class="acct-code">{{ acc.account_number }}</span>
                <span class="type-tag">{{ acc.account_type }}</span>
              </td>
              <td class="num {{ 'debit' if acc.balance < 0 else '' }}">{{ acc.balance_fmt }}</td>
            </tr>
            {% else %}
            <tr class="empty-row"><td colspan="2">No accounts yet</td></tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </section>
  </div>

  <section class="panel">
    <div class="panel-head">
      <h2>Recent ledger entries</h2>
      <span class="hint">last {{ entries|length }}, newest first</span>
    </div>
    <div class="panel-body scroll-x">
      <table>
        <thead>
          <tr>
            <th>Time (UTC)</th>
            <th>Account</th>
            <th>Entry</th>
            <th class="num">Amount</th>
            <th class="num">Running balance</th>
          </tr>
        </thead>
        <tbody>
          {% for e in entries %}
          <tr>
            <td class="ts">{{ e.created_at.strftime('%Y-%m-%d %H:%M:%S') }}</td>
            <td class="acct-code">{{ e.account_number }}</td>
            <td>{{ e.entry_type.capitalize() }}</td>
            <td class="num {{ 'credit' if e.amount > 0 else 'debit' }}">{{ e.amount_fmt }}</td>
            <td class="num">{{ e.running_fmt }}</td>
          </tr>
          {% else %}
          <tr class="empty-row"><td colspan="5">No ledger activity yet</td></tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </section>

  <footer>
    <span>Net position across all accounts should always read $0.00 &mdash; that's the double-entry invariant, not a rounding coincidence.</span>
    <span>{{ account_count }} accounts &middot; {{ entry_count }} entries</span>
  </footer>
</div>

<script>
  const $ = (id) => document.getElementById(id);

  $('swapBtn').addEventListener('click', () => {
    const a = $('sender').value;
    $('sender').value = $('receiver').value;
    $('receiver').value = a;
  });

  $('transferForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const sender = $('sender').value;
    const receiver = $('receiver').value;
    const amount = $('amount').value;
    const resultEl = $('txResult');
    const btn = $('submitBtn');

    resultEl.className = '';
    if (sender === receiver) {
      resultEl.textContent = 'Sender and receiver must be different accounts.';
      resultEl.className = 'err';
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Posting transfer\u2026';
    resultEl.textContent = '';

    try {
      const res = await fetch('/transfer', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ sender_id: sender, receiver_id: receiver, amount })
      });
      const data = await res.json();

      if (res.ok) {
        resultEl.textContent = `Posted \u2014 tx ${data.tx_id.slice(0, 8)}\u2026. Refreshing balances\u2026`;
        resultEl.className = 'ok';
        setTimeout(() => location.reload(), 700);
      } else {
        resultEl.textContent = data.error || 'Transfer failed.';
        resultEl.className = 'err';
        btn.disabled = false;
        btn.textContent = 'Execute atomic transfer';
      }
    } catch (err) {
      resultEl.textContent = 'Could not reach the server. Check your connection and try again.';
      resultEl.className = 'err';
      btn.disabled = false;
      btn.textContent = 'Execute atomic transfer';
    }
  });
</script>
</body>
</html>
"""

ERROR_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Ledger &mdash; Unavailable</title>
<style>
  body{background:#0c1015;color:#e6e9ee;font-family:system-ui,sans-serif;
       display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}
  .box{max-width:480px;padding:2rem;border:1px solid #232b36;border-radius:4px;background:#11161d;}
  h1{font-size:1.1rem;margin-top:0;}
  p{color:#8b95a6;font-size:0.9rem;line-height:1.5;}
  code{color:#c9705f;background:#141a22;padding:0.1rem 0.35rem;border-radius:3px;}
</style>
</head>
<body>
  <div class="box">
    <h1>Can't reach the ledger database</h1>
    <p>The app is up, but the database connection failed. Confirm <code>DATABASE_URL</code> is set and that Postgres is reachable, then reload.</p>
    <p><code>{{ detail }}</code></p>
  </div>
</body>
</html>
"""


@app.route("/")
def index():
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT account_id, account_number, account_type FROM accounts ORDER BY account_number;")
        accounts = cur.fetchall()

        cur.execute("""
            SELECT a.account_id, a.account_number, a.account_type, COALESCE(SUM(l.amount), 0) AS balance
            FROM accounts a
            LEFT JOIN ledger_entries l ON a.account_id = l.account_id
            GROUP BY a.account_id, a.account_number, a.account_type
            ORDER BY a.account_number;
        """)
        balances = cur.fetchall()
        for b in balances:
            b["balance_fmt"] = fmt_money(b["balance"])

        # Running balance per account (window function), most recent entries across all accounts.
        cur.execute("""
            SELECT created_at, account_number, entry_type, amount, running_balance
            FROM (
                SELECT
                    l.created_at,
                    a.account_number,
                    l.entry_type,
                    l.amount,
                    SUM(l.amount) OVER (
                        PARTITION BY l.account_id
                        ORDER BY l.created_at, l.entry_id
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) AS running_balance
                FROM ledger_entries l
                JOIN accounts a ON l.account_id = a.account_id
            ) sub
            ORDER BY created_at DESC
            LIMIT 20;
        """)
        entries = cur.fetchall()
        for e in entries:
            e["amount_fmt"] = fmt_money(e["amount"])
            e["running_fmt"] = fmt_money(e["running_balance"])

        cur.execute("SELECT COALESCE(SUM(amount), 0) AS net FROM ledger_entries;")
        net_position = float(cur.fetchone()["net"])

        cur.close()
        conn.close()

        return render_template_string(
            PAGE_TEMPLATE,
            accounts=accounts,
            balances=balances,
            entries=entries,
            account_count=len(accounts),
            entry_count=len(entries),
            net_position=net_position,
            net_fmt=fmt_money(net_position),
        )
    except psycopg2.OperationalError as e:
        return render_template_string(ERROR_TEMPLATE, detail=str(e).strip()), 503


@app.route("/transfer", methods=["POST"])
def transfer():
    data = request.get_json(silent=True) or {}
    sender_id = data.get("sender_id")
    receiver_id = data.get("receiver_id")
    raw_amount = data.get("amount")

    if not sender_id or not receiver_id:
        return jsonify({"error": "Sender and receiver accounts are required."}), 400
    if sender_id == receiver_id:
        return jsonify({"error": "Sender and receiver must be different accounts."}), 400

    try:
        amount = float(raw_amount)
    except (TypeError, ValueError):
        return jsonify({"error": "Amount must be a number."}), 400
    if amount <= 0:
        return jsonify({"error": "Amount must be greater than zero."}), 400

    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT process_transfer(%s, %s, %s, %s);",
            (sender_id, receiver_id, amount, str(uuid.uuid4())),
        )
        tx_id = cur.fetchone()["process_transfer"]
        conn.commit()
        cur.close()
        return jsonify({"status": "success", "tx_id": str(tx_id)})
    except psycopg2.errors.RaiseException as e:
        # Custom, human-authored messages raised from process_transfer()
        # (e.g. insufficient funds) are safe to surface directly.
        if conn:
            conn.rollback()
        message = str(e).split("\n")[0].replace("ERROR:", "").strip()
        return jsonify({"error": message}), 400
    except psycopg2.OperationalError:
        if conn:
            conn.rollback()
        return jsonify({"error": "Database is unavailable. Try again shortly."}), 503
    except Exception:
        if conn:
            conn.rollback()
        return jsonify({"error": "Transfer could not be completed."}), 400
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))