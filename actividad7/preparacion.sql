-- Actividad 7 - preparacion y restauracion de estados para B07 y B08.
-- pruebas/actividad7.py hace esto solo, en empresas de prueba separadas, y restaura al terminar.
-- Para repetirlo a mano en MySQL sustituir los ids.

-- Revisar los movimientos de la empresa de prueba
SELECT t.id, a.name AS cuenta, t.type, t.amount, t.transaction_date, t.captured_at, t.is_active
FROM transactions t JOIN accounts a ON a.id = t.account_id
WHERE t.company_id = ID_EMPRESA
ORDER BY t.transaction_date, t.id;

-- B07: desactivar un movimiento de prueba (Compra de materiales) y restaurarlo
UPDATE transactions SET is_active = 0 WHERE id = ID_MOVIMIENTO;
UPDATE transactions SET is_active = 1 WHERE id = ID_MOVIMIENTO;

-- B08: desactivar una cuenta con movimientos validos (Caja) y restaurarla
UPDATE accounts SET is_active = 0 WHERE id = ID_CAJA;
UPDATE accounts SET is_active = 1 WHERE id = ID_CAJA;

-- Comprobacion manual del balance (sirve para comparar con la API; las pruebas no lo usan)
SELECT a.id, a.name,
       COALESCE(SUM(CASE WHEN t.transaction_date <  '2026-10-26 00:00:00'
                         THEN IF(t.type = 'INCOME', t.amount, -t.amount) END), 0) AS saldo_inicial,
       COALESCE(SUM(CASE WHEN t.transaction_date >= '2026-10-26 00:00:00' AND t.type = 'INCOME'  THEN t.amount END), 0) AS ingresos,
       COALESCE(SUM(CASE WHEN t.transaction_date >= '2026-10-26 00:00:00' AND t.type = 'EXPENSE' THEN t.amount END), 0) AS egresos
FROM accounts a
LEFT JOIN transactions t
       ON t.account_id = a.id AND t.is_active = 1 AND t.transaction_date < '2026-10-31 00:00:00'
WHERE a.company_id = ID_EMPRESA
GROUP BY a.id, a.name
ORDER BY a.id;
