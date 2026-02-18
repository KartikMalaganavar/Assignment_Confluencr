-- PostgreSQL schema for transactions table
-- Mirrors app/models/transaction.py

-- UUID generator for PRIMARY KEY default.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Create enum only if it does not exist.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type
        WHERE typname = 'transaction_status'
    ) THEN
        CREATE TYPE transaction_status AS ENUM ('PROCESSING', 'PROCESSED', 'FAILED');
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id VARCHAR(128) NOT NULL,
    source_account VARCHAR(128) NOT NULL,
    destination_account VARCHAR(128) NOT NULL,
    amount NUMERIC(18, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    status transaction_status NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMPTZ NULL,
    processing_started_at TIMESTAMPTZ NULL,
    error_message TEXT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    duplicate_conflict_count INTEGER NOT NULL DEFAULT 0,
    last_conflict_at TIMESTAMPTZ NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_transactions_transaction_id
    ON transactions (transaction_id);

CREATE INDEX IF NOT EXISTS ix_transactions_status
    ON transactions (status);

CREATE INDEX IF NOT EXISTS ix_transactions_status_processing_started_at
    ON transactions (status, processing_started_at);

-- Keep updated_at in sync for UPDATE statements issued outside SQLAlchemy.
CREATE OR REPLACE FUNCTION set_transactions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_transactions_updated_at ON transactions;

CREATE TRIGGER trg_transactions_updated_at
BEFORE UPDATE ON transactions
FOR EACH ROW
EXECUTE FUNCTION set_transactions_updated_at();
