CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Accounts Table
CREATE TABLE accounts (
    account_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_number VARCHAR(20) UNIQUE NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    account_type VARCHAR(20) NOT NULL CHECK (account_type IN ('CUSTOMER', 'SETTLEMENT', 'FEES', 'ESCROW')),
    status VARCHAR(15) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'FROZEN', 'CLOSED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Transaction Headers
CREATE TABLE transactions (
    transaction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference_id VARCHAR(64) UNIQUE NOT NULL,
    description TEXT,
    status VARCHAR(15) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'POSTED', 'FAILED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Partitioned Double-Entry Ledger
CREATE TABLE ledger_entries (
    entry_id UUID DEFAULT uuid_generate_v4(),
    transaction_id UUID NOT NULL REFERENCES transactions(transaction_id) ON DELETE RESTRICT,
    account_id UUID NOT NULL REFERENCES accounts(account_id) ON DELETE RESTRICT,
    amount NUMERIC(18, 4) NOT NULL CHECK (amount <> 0),
    entry_type VARCHAR(6) NOT NULL CHECK (entry_type IN ('DEBIT', 'CREDIT')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (entry_id, created_at)
) PARTITION BY RANGE (created_at);

-- 2026 Quarterly Partitions
CREATE TABLE ledger_entries_2026_q1 PARTITION OF ledger_entries
    FOR VALUES FROM ('2026-01-01 00:00:00+00') TO ('2026-04-01 00:00:00+00');
CREATE TABLE ledger_entries_2026_q2 PARTITION OF ledger_entries
    FOR VALUES FROM ('2026-04-01 00:00:00+00') TO ('2026-07-01 00:00:00+00');
CREATE TABLE ledger_entries_2026_q3 PARTITION OF ledger_entries
    FOR VALUES FROM ('2026-07-01 00:00:00+00') TO ('2026-10-01 00:00:00+00');
CREATE TABLE ledger_entries_2026_q4 PARTITION OF ledger_entries
    FOR VALUES FROM ('2026-10-01 00:00:00+00') TO ('2027-01-01 00:00:00+00');

-- Targeted Indexes
CREATE INDEX idx_ledger_account_lookup ON ledger_entries (account_id, created_at DESC);
CREATE INDEX idx_active_accounts ON accounts (account_number) WHERE status = 'ACTIVE';
CREATE INDEX idx_tx_reference ON transactions (reference_id);

-- Deadlock-Free Transfer Function
CREATE OR REPLACE FUNCTION process_transfer(
    p_sender_id UUID,
    p_receiver_id UUID,
    p_amount NUMERIC,
    p_idempotency_key VARCHAR
) 
RETURNS UUID AS $$
DECLARE
    v_tx_id UUID;
    v_first_lock UUID;
    v_second_lock UUID;
    v_sender_balance NUMERIC;
BEGIN
    IF p_amount <= 0 THEN
        RAISE EXCEPTION 'Transfer amount must be strictly positive';
    END IF;

    IF p_sender_id = p_receiver_id THEN
        RAISE EXCEPTION 'Sender and Receiver accounts must be distinct';
    END IF;

    -- Consistent lock ordering prevents deadlocks under concurrency
    IF p_sender_id < p_receiver_id THEN
        v_first_lock := p_sender_id;
        v_second_lock := p_receiver_id;
    ELSE
        v_first_lock := p_receiver_id;
        v_second_lock := p_sender_id;
    END IF;

    PERFORM 1 FROM accounts WHERE account_id = v_first_lock FOR UPDATE;
    PERFORM 1 FROM accounts WHERE account_id = v_second_lock FOR UPDATE;

    SELECT COALESCE(SUM(amount), 0) INTO v_sender_balance
    FROM ledger_entries
    WHERE account_id = p_sender_id;

    IF v_sender_balance < p_amount THEN
        RAISE EXCEPTION 'Insufficient funds: Available %, Required %', v_sender_balance, p_amount;
    END IF;

    INSERT INTO transactions (reference_id, description, status)
    VALUES (p_idempotency_key, 'Transfer', 'POSTED')
    RETURNING transaction_id INTO v_tx_id;

    INSERT INTO ledger_entries (transaction_id, account_id, amount, entry_type)
    VALUES 
        (v_tx_id, p_sender_id, -p_amount, 'DEBIT'),
        (v_tx_id, p_receiver_id, p_amount, 'CREDIT');

    RETURN v_tx_id;
END;
$$ LANGUAGE plpgsql;