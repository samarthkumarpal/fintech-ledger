-- Create base accounts
INSERT INTO accounts (account_number, account_type) 
VALUES ('ACC_ALICE', 'CUSTOMER'), ('ACC_BOB', 'CUSTOMER')
ON CONFLICT (account_number) DO NOTHING;

INSERT INTO accounts (account_number, account_type) 
VALUES ('ACC_SYSTEM_VAULT', 'SETTLEMENT')
ON CONFLICT (account_number) DO NOTHING;

-- Seed Alice with initial $10,000 from Vault
DO $$
DECLARE
    v_vault UUID;
    v_alice UUID;
    v_tx UUID;
BEGIN
    SELECT account_id INTO v_vault FROM accounts WHERE account_number = 'ACC_SYSTEM_VAULT';
    SELECT account_id INTO v_alice FROM accounts WHERE account_number = 'ACC_ALICE';

    IF NOT EXISTS (SELECT 1 FROM transactions WHERE reference_id = 'INIT_DEPOSIT_ALICE_001') THEN
        INSERT INTO transactions (reference_id, description, status)
        VALUES ('INIT_DEPOSIT_ALICE_001', 'Initial Funding', 'POSTED')
        RETURNING transaction_id INTO v_tx;

        INSERT INTO ledger_entries (transaction_id, account_id, amount, entry_type)
        VALUES 
            (v_tx, v_vault, -10000.00, 'DEBIT'),
            (v_tx, v_alice, 10000.00, 'CREDIT');
    END IF;
END $$;