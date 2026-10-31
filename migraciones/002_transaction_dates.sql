-- Actividad 7: fecha de operacion, fecha de captura, estado del movimiento e indice para los balances.
-- main.py lo aplica al arrancar si falta. Las fechas se guardan sin zona y por convencion son UTC.
-- Las filas previas toman created_at como fecha de operacion y de captura.

ALTER TABLE transactions ADD COLUMN transaction_date DATETIME NULL;
UPDATE transactions SET transaction_date = created_at;
ALTER TABLE transactions MODIFY transaction_date DATETIME NOT NULL;

ALTER TABLE transactions ADD COLUMN captured_at DATETIME NULL;
UPDATE transactions SET captured_at = created_at;
ALTER TABLE transactions MODIFY captured_at DATETIME NOT NULL;

ALTER TABLE transactions ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1;

CREATE INDEX ix_transactions_account_date ON transactions (account_id, transaction_date);
