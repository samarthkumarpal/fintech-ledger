-- 1. Account Balances Check
SELECT 
    a.account_number, 
    COALESCE(SUM(l.amount), 0) AS balance
FROM accounts a
LEFT JOIN ledger_entries l ON a.account_id = l.account_id
GROUP BY a.account_number;

-- 2. Audit Trail & Running Balance (Window Function)
SELECT 
    created_at,
    amount,
    entry_type,
    SUM(amount) OVER (
        PARTITION BY account_id 
        ORDER BY created_at 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_balance
FROM ledger_entries
WHERE account_id = (SELECT account_id FROM accounts WHERE account_number = 'ACC_ALICE')
ORDER BY created_at;

-- 3. Execution Plan / Query Profile (Run this for README metrics)
EXPLAIN (ANALYZE, BUFFERS)
SELECT 
    created_at,
    amount,
    SUM(amount) OVER (
        PARTITION BY account_id 
        ORDER BY created_at 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_balance
FROM ledger_entries
WHERE account_id = (SELECT account_id FROM accounts WHERE account_number = 'ACC_ALICE');