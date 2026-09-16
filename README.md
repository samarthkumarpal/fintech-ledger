# High-Concurrency Double-Entry FinTech Ledger Engine

A production-ready core banking ledger implemented in PostgreSQL 16. It ensures zero balance drift, guarantees ACID transactional integrity, and prevents deadlocks under high-concurrency workloads using deterministic locking and range partitioning.

---

## 1. Verified Balances & Ledger Audit Trail

Synthetic test accounts showing balanced settlement debits and credited customer funds:

```text
 account_number   |   balance    
------------------+--------------
 ACC_ALICE        |    9500.0000
 ACC_SYSTEM_VAULT |  -10000.0000
 ACC_BOB          |     500.0000
(3 rows)
```

### Running Balance Audit (Window Function)
Each transaction computes point-in-time balances dynamically without destructive row updates:

```text
          created_at           |    amount   | entry_type | running_balance 
-------------------------------+-------------+------------+-----------------
 2026-09-16 10:15:33.887902+00 |  10000.0000 | CREDIT     |      10000.0000
 2026-09-16 10:15:55.534223+00 |    -10.0000 | DEBIT      |       9990.0000
 2026-09-16 10:15:55.55284+00  |    -10.0000 | DEBIT      |       9980.0000
 2026-09-16 10:15:55.603016+00 |    -10.0000 | DEBIT      |       9970.0000
 2026-09-16 10:15:55.603066+00 |    -10.0000 | DEBIT      |       9960.0000
 2026-09-16 10:15:55.603123+00 |    -10.0000 | DEBIT      |       9950.0000
 2026-09-16 10:15:55.603563+00 |    -10.0000 | DEBIT      |       9940.0000
 2026-09-16 10:15:55.603785+00 |    -10.0000 | DEBIT      |       9930.0000
 2026-09-16 10:15:55.62309+00  |    -10.0000 | DEBIT      |       9920.0000
 2026-09-16 10:15:55.627343+00 |    -10.0000 | DEBIT      |       9910.0000
 2026-09-16 10:15:55.627482+00 |    -10.0000 | DEBIT      |       9900.0000
 2026-09-16 10:15:55.627601+00 |    -10.0000 | DEBIT      |       9890.0000
 2026-09-16 10:15:55.629287+00 |    -10.0000 | DEBIT      |       9880.0000
```

---

## 2. Query Performance Profiling (`EXPLAIN ANALYZE`)

Execution plan demonstrating partition scanning, index utilization, and high shared buffer hits:

```text
Recheck Cond: (account_id = $0)
Buffers: shared hit=2
  -> Bitmap Index Scan on ledger_entries_2026_q2_account_id_created_at_idx (cost=0.00..4.17 rows=3 width=0) (actual time=0.000..0.000 rows=0 loops=1)
       Index Cond: (account_id = $0)
       Buffers: shared hit=2
  -> Seq Scan on ledger_entries_2026_q3 ledger_entries_3 (cost=0.00..5.72 rows=73 width=31) (actual time=0.003..0.017 rows=109 loops=1)
       Filter: (account_id = $0)
       Rows Removed by Filter: 109
       Buffers: shared hit=3
  -> Bitmap Heap Scan on ledger_entries_2026_q4 ledger_entries_4 (cost=4.17..11.28 rows=3 width=31) (actual time=0.001..0.001 rows=0 loops=1)
       Recheck Cond: (account_id = $0)
       Buffers: shared hit=2
  -> Bitmap Index Scan on ledger_entries_2026_q4_account_id_created_at_idx (cost=0.00..4.17 rows=3 width=0) (actual time=0.000..0.001 rows=0 loops=1)
       Index Cond: (account_id = $0)
       Buffers: shared hit=2

Planning:
  Buffers: shared hit=6
  Planning Time: 0.108 ms
  Execution Time: 0.120 ms
(38 rows)
```

---

## Technical Highlights

* **Double-Entry Bookkeeping:** Balances are never modified in place; all transfers generate balanced credit/debit record pairs ensuring zero balance drift.
* **Deadlock Mitigation:** Row locks (`SELECT ... FOR UPDATE`) are acquired in deterministic alphabetical order by `UUID`, eliminating cyclical wait conditions across concurrent transactions.
* **Declarative Partitioning:** `ledger_entries` is range-partitioned quarterly to isolate hot transactional data from historical audit logs.
* **Sub-Millisecond Execution:** Planning and execution latency clocked under `0.23 ms` with 100% memory buffer hits.