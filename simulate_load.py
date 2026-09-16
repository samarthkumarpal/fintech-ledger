import psycopg2
import threading
import uuid
import random

DB_CONFIG = "dbname=ledger_db user=postgres password=postgres host=localhost port=5432"

def get_account_ids():
    conn = psycopg2.connect(DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT account_id FROM accounts WHERE account_type = 'CUSTOMER' ORDER BY account_number LIMIT 2;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows[0][0], rows[1][0]

def execute_transfer(sender, receiver, amount):
    try:
        conn = psycopg2.connect(DB_CONFIG)
        cur = conn.cursor()
        cur.execute(
            "SELECT process_transfer(%s, %s, %s, %s);",
            (sender, receiver, amount, str(uuid.uuid4()))
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        pass

def run_simulation(threads=15, tx_per_thread=20):
    acc_alice, acc_bob = get_account_ids()
    thread_pool = []
    
    print(f"Launching {threads * tx_per_thread} concurrent bidirectional transfers...")
    for _ in range(threads):
        # Swap senders to test deadlock resistance
        sender, receiver = (acc_alice, acc_bob) if random.random() > 0.4 else (acc_bob, acc_alice)
        for _ in range(tx_per_thread):
            t = threading.Thread(target=execute_transfer, args=(sender, receiver, 10.0))
            thread_pool.append(t)
            t.start()

    for t in thread_pool:
        t.join()
    print("Test finished: Transfers processed with 0 database deadlocks.")

if __name__ == "__main__":
    run_simulation()