# Evidencias - Actividad 7: balances por cuenta y balance general

Integrantes: Roberto Balmes Solis, David Romero

Generado por `python pruebas/actividad7.py` el 2026-10-31 01:30 UTC. Cada caso adicional usa su propia empresa de prueba,
asi el conjunto de referencia (Banco, Caja, Ahorro) no se altera. Los resultados completos estan en
`pruebas/resultados_actividad7.json` y las pruebas automatizadas en `tests/test_balances.py`
(salida en `actividad7/salida_tests.txt`).

Periodo de referencia: 2026-10-26 al 2026-10-30, dias completos en UTC.

## B01. Consultar Banco, Caja, Ahorro y el general del 26 al 30

- **Resultado:** correcto
- **Obtenido:** Banco: inicial 1000.00, ingresos 3000.00, egresos 2200.00, profit 800.00, final 1800.00, enRojo false; Caja: inicial 0.00, ingresos 500.00, egresos 700.00, profit -200.00, final -200.00, enRojo true; Ahorro: inicial 0.00, ingresos 0.00, egresos 0.00, profit 0.00, final 0.00, enRojo false; General: inicial 1000.00, ingresos 3500.00, egresos 2900.00, profit 600.00, final 1600.00, enRojo false, accountsInRed 1; filas de transactions iguales antes y despues: True
- **Regla comprobada:** El saldo inicial sale de los movimientos anteriores al periodo y consultar no guarda ni modifica filas

## B02. Consultar Banco unicamente el 28

- **Resultado:** correcto
- **Obtenido:** Banco 28: inicial 2800.00, ingresos 0.00, egresos 1000.00, profit -1000.00, final 1800.00, enRojo false
- **Regla comprobada:** Un profit negativo del dia no implica saldo final negativo

## B03. Consultar una empresa sin cuentas

- **Resultado:** correcto
- **Obtenido:** accounts [], inicial 0.00, ingresos 0.00, egresos 0.00, profit 0.00, final 0.00, enRojo false, accountsInRed 0
- **Regla comprobada:** Sin cuentas el general devuelve ceros, no null

## B04. Movimientos 25 23:59:59, 26 00:00:00, 30 23:59:59 y 31 00:00:00 (1, 10, 100 y 1000)

- **Resultado:** correcto
- **Obtenido:** inicial 1.00, ingresos 110.00, egresos 0.00, profit 110.00, final 111.00, enRojo false
- **Regla comprobada:** Inicio incluido y fin excluido: [26 00:00Z, 31 00:00Z); el del 31 queda fuera

## B05. Capturar un egreso del 27 con capturedAt posterior

- **Resultado:** correcto
- **Obtenido:** transactionDate 2026-10-27T12:00:00+00:00, capturedAt 2026-10-31T01:30:08+00:00; Banco 26-30 egresos 2300.00, final 1700.00; Banco solo 27 egresos 1300.00
- **Regla comprobada:** El movimiento cuenta en el dia de transactionDate, no en el de captura

## B06. Ingresos 0.10 y 0.20 y egreso 0.30 en una cuenta vacia

- **Resultado:** correcto
- **Obtenido:** inicial 0.00, ingresos 0.30, egresos 0.30, profit 0.00, final 0.00, enRojo false
- **Regla comprobada:** Decimal sin float: 0.10 + 0.20 - 0.30 da exactamente 0.00

## B07. Desactivar el movimiento 55 (Compra de materiales 1000.00) y volver a consultar

- **Resultado:** correcto
- **Obtenido:** Banco con el movimiento inactivo: inicial 1000.00, ingresos 3000.00, egresos 1200.00, profit 1800.00, final 2800.00, enRojo false; general final 2600.00; al reactivarlo Banco vuelve a 1800.00
- **Regla comprobada:** Un movimiento inactivo no participa; los demas se conservan

## B08. Desactivar Caja, que tiene movimientos validos

- **Resultado:** correcto
- **Obtenido:** Caja: isActive false, final -200.00; general final 1600.00, accountsInRed 1
- **Regla comprobada:** Desactivar una cuenta no borra su historial; sigue sumando al general

## B09. Agregar dos conceptos mas a Banco sin movimientos nuevos

- **Resultado:** correcto
- **Obtenido:** General antes: inicial 1000.00, ingresos 3500.00, egresos 2900.00, profit 600.00, final 1600.00, enRojo false; despues: inicial 1000.00, ingresos 3500.00, egresos 2900.00, profit 600.00, final 1600.00, enRojo false
- **Regla comprobada:** El calculo no se une a account_concepts, asi que no se duplican importes

## B10. fromDate posterior a toDate y fecha inexistente 2026-02-30

- **Resultado:** correcto
- **Obtenido:** accountBalance: fromDate no puede ser posterior a toDate; generalBalance: fromDate no puede ser posterior a toDate; 2026-02-30: Variable '$from' has invalid value: Value cannot represent a Date: "2026-02-30". day is out of range for month
- **Regla comprobada:** Las fechas se validan antes de calcular; no se devuelve un balance

## B11. Consultar sin token, con token alterado y con token vencido

- **Resultado:** correcto
- **Obtenido:** sin token: Falta el token / Falta el token; alterado: El token no es valido / El token no es valido; vencido: El token no es valido / El token no es valido
- **Regla comprobada:** Las dos consultas validan el token antes de devolver informacion

## B12. Token de la empresa A con el id de Banco de la empresa B; despues el general de A

- **Resultado:** correcto
- **Obtenido:** cuenta de B: Cuenta no disponible (data null); cuenta inexistente: Cuenta no disponible; general de A solo trae sus cuentas: True
- **Regla comprobada:** Una cuenta ajena y una inexistente responden igual y no se revelan datos de otra empresa

## B13. Rol CONSULTA: leer balances y despues intentar createTransaction

- **Resultado:** correcto
- **Obtenido:** accountBalance Banco final 1800.00; general final 1600.00; createTransaction: El rol no tiene el permiso transactions.write; movimientos 6 -> 6
- **Regla comprobada:** accounts.read y transactions.read bastan para leer; capturar sigue pidiendo transactions.write

## B14. Quitar transactions.read a CONSULTA conservando accounts.read, con el mismo token

- **Resultado:** correcto
- **Obtenido:** accountBalance: El rol no tiene el permiso transactions.read; generalBalance: El rol no tiene el permiso transactions.read; permiso restaurado y vuelve a leer: True
- **Regla comprobada:** El permiso se lee en MySQL en cada peticion; faltando uno de los dos se rechaza

## B15. Egreso de 50.00 en una cuenta vacia de una empresa sin otros saldos

- **Resultado:** correcto
- **Obtenido:** Cuenta: inicial 0.00, ingresos 0.00, egresos 50.00, profit -50.00, final -50.00, enRojo true; general final -50.00, isInRed true, accountsInRed 1
- **Regla comprobada:** Se permite dejar saldo negativo y el backend lo informa; el monto se guarda positivo y EXPENSE resta
