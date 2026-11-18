-- Unidad III · Actividad 2 · Comprobacion de idempotencia en MySQL (empresa 1, Papeleria El Cuaderno)
-- Correr: docker compose exec -T mysql mysql -uingresos -pingresos ingresos < unidad3_actividad2/comprobacion_mysql.sql

-- 1) Las llaves guardadas y el movimiento al que apuntan
SELECT k.idem_key, k.transaction_id, LEFT(k.request_hash, 12) AS hash, k.created_at
FROM idempotency_keys k
WHERE k.company_id = 1
ORDER BY k.id;

-- 2) Movimientos de la renta de noviembre: hay dos (uno por llave), no tres ni cuatro
SELECT t.id, t.type, t.amount, t.description, t.transaction_date
FROM transactions t
WHERE t.company_id = 1 AND t.description = 'Renta noviembre - prueba de idempotencia'
ORDER BY t.id;

-- 3) Cuantos movimientos hay por llave: siempre 1
SELECT k.idem_key, COUNT(t.id) AS movimientos
FROM idempotency_keys k
JOIN transactions t ON t.id = k.transaction_id
WHERE k.company_id = 1
GROUP BY k.idem_key;
