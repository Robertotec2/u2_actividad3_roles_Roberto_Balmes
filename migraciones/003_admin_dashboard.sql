-- Unidad 3 Actividad 2: datos de cuentas y conceptos para el dashboard administrativo
-- e idempotencia de createTransaction. main.py lo aplica al arrancar si falta.

ALTER TABLE accounts ADD COLUMN account_type VARCHAR(20) NOT NULL DEFAULT 'OTHER';
-- Cuentas previas (solo tenian nombre): se toma el tipo evidente del nombre
UPDATE accounts SET account_type = 'CASH' WHERE name = 'Caja';
UPDATE accounts SET account_type = 'DEBIT' WHERE name = 'Banco';
UPDATE accounts SET account_type = 'SAVINGS' WHERE name = 'Ahorro';
ALTER TABLE accounts ADD COLUMN bank_name VARCHAR(100) NULL;
ALTER TABLE accounts ADD COLUMN clabe VARCHAR(18) NULL;
ALTER TABLE accounts ADD COLUMN description VARCHAR(255) NULL;

ALTER TABLE concepts ADD COLUMN description VARCHAR(255) NULL;

-- Una llave por (empresa, operacion, llave). La llave y el movimiento se confirman en el mismo COMMIT.
CREATE TABLE idempotency_keys (
  id INT AUTO_INCREMENT PRIMARY KEY,
  company_id INT NOT NULL,
  operation VARCHAR(50) NOT NULL,
  idem_key VARCHAR(100) NOT NULL,
  request_hash CHAR(64) NOT NULL,
  transaction_id INT NOT NULL,
  company_user_id INT NOT NULL,
  created_at DATETIME NOT NULL,
  CONSTRAINT uq_idempotency_key UNIQUE (company_id, operation, idem_key),
  FOREIGN KEY (company_id) REFERENCES companies (id),
  FOREIGN KEY (transaction_id) REFERENCES transactions (id),
  FOREIGN KEY (company_user_id) REFERENCES company_users (id)
);
