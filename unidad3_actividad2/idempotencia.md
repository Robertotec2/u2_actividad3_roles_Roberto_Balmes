# Parte 1 · Idempotencia en `createTransaction`

Equipo: Roberto Balmes Solís y David Romero

## Qué es y por qué la necesitamos

Una operación es **idempotente** cuando repetirla deja el mismo efecto que hacerla una vez. Leer (`accounts`,
`companyUsers`, `generalBalance`) ya lo es: pedir el inventario cinco veces no crea cinco inventarios.
`createTransaction` no lo era: hace un `INSERT` y mueve el balance. Si el `COMMIT` ya pasó pero la respuesta no llegó
(red cortada, timeout, doble clic en Guardar), el cliente reintenta y el servidor lo cuenta como **otro egreso**.

GraphQL manda todo por `POST`, así que el método HTTP no ayuda: la idempotencia se decide en la operación, no en el verbo.

El servidor no puede adivinar mirando el monto: **dos rentas de 100 pueden ser legítimas**. Por eso el cliente manda una
**llave por acción** (por ejemplo un UUID generado al pulsar Guardar). Si reintenta, manda la misma llave; si el usuario
captura otro gasto, genera otra.

## Cómo quedó implementado

```
cliente ──createTransaction(input + idempotencyKey)──▶ resolver
                                                        │
                    ┌───────────── ¿la llave ya está en idempotency_keys? ─────────────┐
                    │ sí                                                                │ no
        ¿mismo hash del cuerpo?                                    INSERT movimiento + UPDATE balance
          │ sí              │ no                                   INSERT llave (hash, transaction_id)
  devolver el mismo     error "Esa idempotencyKey                  ── un solo COMMIT ──
  movimiento (mismo id)  ya se uso con otros datos"                 │
                                                       si el índice único rechaza la llave (dos envíos
                                                       simultáneos): ROLLBACK y devolver el movimiento guardado
```

| Pieza | Dónde |
|---|---|
| Tabla `idempotency_keys` (`company_id`, `operation`, `idem_key`, `request_hash`, `transaction_id`, `company_user_id`, `created_at`) | `models.py` → `IdempotencyKeyModel`, `migraciones/003_admin_dashboard.sql` |
| Índice único `uq_idempotency_key (company_id, operation, idem_key)` | la misma tabla |
| `idempotencyKey: String` en `CreateTransactionInput` (8 a 100 caracteres) | `schema.py` |
| Hash SHA-256 del cuerpo **tal como lo mandó el cliente** (cuenta, concepto, monto, descripción, fecha) | `huella_movimiento` |
| Movimiento y llave en la misma sesión con un solo `db.commit()` | `Mutation.create_transaction` |

Decisiones:

- **La llave vive en MySQL, no en Redis.** La memoria de la llave y el dinero tienen que confirmarse juntos: si el
  `COMMIT` falla no queda ni el gasto ni la llave; si pasa y se pierde la respuesta, el reintento encuentra la llave.
  Con Redis podría quedar “ya cobré” en la caché y un rollback en MySQL, o al revés.
- **El hash se calcula del cuerpo enviado, no de lo que calcula el servidor.** Si no se manda `transactionDate`, el
  servidor usa la hora actual; si eso entrara al hash, cada reintento tendría un hash distinto.
- **Misma llave con otros datos = error**, no se reutiliza el movimiento anterior.
- **Primero se valida el permiso `transactions.write` y después se busca la llave**, para que alguien sin permiso no
  pueda leer movimientos ajenos adivinando llaves. La llave es por empresa: otra empresa con la misma llave no choca.
- **`idempotencyKey` es opcional** para no romper los scripts de la Unidad II (`pruebas/actividad4.py` … `actividad7.py`).
  Sin llave el comportamiento es el de antes (cada envío es un movimiento). Todo cliente nuevo debe mandarla.

## Idempotencia no es protección contra DoS

La idempotencia hace **seguro el reintento**, no frena un ataque: mil llaves distintas siguen siendo mil movimientos.
Lo que frena el abuso es el límite de peticiones (rate limiting), el timeout y el permiso `transactions.write`.
Son problemas distintos y conviene tener los dos.

## Comprobación

| Prueba | Resultado |
|---|---|
| GraphiQL: la misma mutación dos veces con la misma llave | mismo `id` **64** las dos veces (capturas 01 y 02) |
| GraphiQL: misma mutación y monto con **otra** llave | movimiento nuevo, `id` **65** (captura 03) |
| GraphiQL: la primera llave con monto 250.00 | `Esa idempotencyKey ya se uso con otros datos` (captura 04) |
| MySQL: filas por llave | 1 y 1 (`salida_mysql_idempotencia.txt`) |
| `tests/test_idempotencia.py` | 6 pruebas OK, incluida la de **5 envíos simultáneos con la misma llave → 1 fila y el balance movido una sola vez** |

```bash
python -m unittest -v tests.test_idempotencia
docker compose exec -T mysql mysql -t -uingresos -pingresos ingresos < unidad3_actividad2/comprobacion_mysql.sql
```
