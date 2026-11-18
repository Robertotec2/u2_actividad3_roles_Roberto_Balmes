# Sistema General de Ingresos

Integrantes: Roberto Balmes Solis, David Romero

## Unidad 3 Actividad 2 - Dashboard administrativo e idempotencia (lo mas reciente)

Mismo cliente de `dashboard/`, con un menu: **Dashboard financiero** (actividad 1) y **Dashboard administrativo**
(Usuarios, Cuentas, Conceptos). Mismos comandos de arranque que abajo; la migracion `003` se aplica sola al arrancar.

- Entrar en http://localhost:8000/dashboard/ con `roberto.demo@ingresos.test` / `demo123` (ADMINISTRADOR, el rol con el
  que probamos la escritura) y elegir la seccion en el menu. `david.demo@ingresos.test` (CONSULTA) ve las tablas sin botones.
- `createTransaction` acepta `idempotencyKey`: la misma llave devuelve el mismo movimiento; la llave y el movimiento se
  guardan en el mismo COMMIT (tabla `idempotency_keys`). Pruebas: `python -m unittest -v tests.test_idempotencia`.
- Backend nuevo: `accountConcepts`, `removeConceptFromAccount`, `mySession.permissions`, `activeOnly` en `accounts` y
  `concepts`, y campos de cuenta `accountType`, `bankName`, `clabeMasked`, `description`.

| Entregable | Archivo |
|---|---|
| README corto (como entrar, rol de prueba) | `unidad3_actividad2/README.md` |
| Idempotencia explicada | `unidad3_actividad2/idempotencia.md` |
| Evidencias y capturas | `unidad3_actividad2/evidencias.md` y `unidad3_actividad2/capturas/` |
| Guion de la demo final | `unidad3_actividad2/guion_demo.md` |

## Unidad 3 Actividad 1 - Dashboard financiero

Cliente web (HTML + CSS + JavaScript, sin dependencias) en `dashboard/`, servido por el mismo FastAPI.

```
cp .env.example .env                                      # primera vez; poner JWT_SECRET
docker compose up --build                                 # MySQL en localhost:3307, API en localhost:8000
python pruebas/u3_actividad1_datos.py                     # datos de demostracion (una sola vez)
```

- Dashboard: http://localhost:8000/dashboard/ (la raiz redirige ahi) · GraphiQL: http://localhost:8000/graphql
- Usuario de prueba: `roberto.demo@ingresos.test` / `demo123` (ADMINISTRADOR). Tambien `david.demo@ingresos.test`
  (CONSULTA) e `invitado.demo@ingresos.test` (sin rol, ve "Acceso denegado"). Misma contrasena de laboratorio.
- Periodo de demostracion: 2026-10-26 al 2026-10-30 -> inicial 1,000.00, ingresos 3,500.00, egresos 2,900.00,
  profit 600.00, final 1,600.00, general no en rojo, 1 cuenta en rojo (Caja).
- Para empezar de cero: `docker compose down -v` y volver a correr los dos ultimos comandos.

Cambios al backend: query `mySession` (empresa, usuario y rol del token, sin datos financieros), `/dashboard`
como archivos estaticos y CORS opcional con `CORS_ORIGINS` (solo si el dashboard se sirve en otro puerto).
Detalle del cliente en `dashboard/README.md`.

| Entregable | Archivo |
|---|---|
| Boceto | `unidad3_actividad1/boceto_dashboard.png` (tambien `.pdf` y `.svg`) |
| Evidencias | `unidad3_actividad1/evidencias.md` y `unidad3_actividad1/capturas/` |
| Guion de la demo | `unidad3_actividad1/guion_demo.md` |

---

# Unidad 2 - Roles y control de acceso

Unidad 2 Actividad 3. Se agregaron roles, permisos y la matriz de permisos por rol encima del sistema de empresas, usuarios, cuentas, conceptos y movimientos.

## Como correrlo

Desde la actividad 6 hace falta el secreto del token en `.env` (no se sube a Git):

```
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"   # pegar el valor en JWT_SECRET
docker compose up --build
```

Luego entrar a http://localhost:8000/graphql

Sin docker (con MySQL local):

```
pip install -r requirements.txt
set DATABASE_URL=mysql+pymysql://ingresos:ingresos@localhost:3306/ingresos
set JWT_SECRET=el_valor_generado
uvicorn main:app --reload
```

## Que se agrego

- Tablas `roles`, `permissions`, `role_permissions` y `company_user_roles`
- Al arrancar se cargan los 4 roles, los 10 permisos y la matriz si las tablas estan vacias (no se duplican al reiniciar)
- Queries: `roles`, `role`, `permissions`, `rolePermissions`
- Mutations: `createRole`, `deactivateRole`, `createPermission`, `assignPermissionToRole`, `removePermissionFromRole`, `assignRole`
- `createCompanyAdmin` deja `isAdmin = true` y asigna el rol ADMINISTRADOR
- `exigir_permiso` revisa membresia -> rol activo -> permisos del rol antes del commit en createCompanyUser, deactivateCompanyUser, createAccount, createConcept, assignConceptToAccount, createTransaction, assignRole y assignPermissionToRole
- Las consultas de cuentas, conceptos y movimientos piden el permiso `.read`

## Datos de prueba que usamos

| companyUserId | Usuario | Empresa | Rol |
|---|---|---|---|
| 1 | Roberto Balmes | Papeleria El Cuaderno | ADMINISTRADOR |
| 2 | Luis Pech | Taller Mecanico Hnos. Pech | ADMINISTRADOR |
| 3 | David Romero | Papeleria El Cuaderno | CONTADOR |
| 4 | Ana Canul | Papeleria El Cuaderno | CAPTURISTA (despues CONTADOR) |
| 5 | Mario Chi | Papeleria El Cuaderno | CONSULTA |

Integrantes: Roberto Balmes Solis, David Romero

## Actividad 4 - Configuracion de permisos para diferentes roles

Mismo proyecto. Solo cambio `assignPermissionToRole`: si la pareja rol-permiso ya existia inactiva la vuelve a activar en vez de crear otra fila.

Para correr las pruebas (con la base vacia y el servidor arriba):

```
python pruebas/actividad4.py
```

Arma la empresa con Ana (ADMINISTRADOR), Luis (CONTADOR), Maria y Jose (CAPTURISTA) y Pedro (CONSULTA) y corre las 4 partes:

1. Revisa la lista de los 4 roles contra la tabla
2. Agrega `accounts.write` a CAPTURISTA, Maria y Jose crean cuentas, se quita y los dos vuelven a ser rechazados (la fila queda `is_active = 0`)
3. Pedro es rechazado como CONSULTA, `assignRole` lo pasa a CAPTURISTA y ya registra el movimiento; CONTADOR y CONSULTA no cambian
4. Jose no puede cambiar la lista, Ana si

Los resultados quedan en `pruebas/resultados.json`. Si tu MySQL no esta en el puerto 3307 cambia `MYSQL_CMD`.

SELECT final:

```sql
SELECT r.code AS rol, p.code AS permiso, rp.is_active
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
ORDER BY r.code, p.code;
```

## Actividad 5 - Configurar permisos con GraphQL

Integrantes: Roberto Balmes Solis, David Romero

Se agregaron tres funcionalidades. La validacion y el calculo de diferencias estan en `configuracion.py` y los usan la query y la mutation, asi no pueden dar resultados distintos:

- `permissionCatalog(actorCompanyUserId, resource)`: catalogo activo, filtrado en MySQL por el prefijo del enum `PermissionResource` (pide `roles.read`)
- `previewRolePermissions(input, actorCompanyUserId)`: valida la lista y regresa `current`, `toActivate`, `toDeactivate`, `unchanged` y `finalCount` sin escribir nada (pide `roles.read`)
- `setRolePermissions(input, actorCompanyUserId)`: vuelve a validar y deja exactamente esa lista con un solo `commit`; si se repite regresa `changed: false` (pide `roles.write`)

Reglas: el rol tiene que existir, estar activo y no ser ADMINISTRADOR; cada permiso tiene que existir y estar activo; ids repetidos dan error (`"3"` y `3` cuentan igual); `[]` es valido y desactiva todo. Reactivar usa la misma fila.

Se agrego `UNIQUE (role_id, permission_id)` en `role_permissions`. Como `create_all` no cambia tablas que ya existen, `main.py` la agrega al arrancar si falta; el SQL esta en `migraciones/001_unique_role_permissions.sql`. La carga inicial solo llena un rol que no tiene ninguna fila, asi que una lista vacia sigue vacia al reiniciar.

Archivos en `actividad5/`:

| Archivo | Que es |
|---|---|
| `investigacion.md` | Investigacion de los cuatro apartados con fuentes |
| `operaciones.graphql` | Operaciones con nombre (alias y fragmento en `ExplorarCatalogo`) |
| `operaciones_error.graphql` | `CatalogoRecursoInexistente` con `PAYMENTS` (va aparte porque GraphQL valida todo el documento) |
| `variables/` | Un JSON por caso |
| `configuracion_inicial.json` / `configuracion_final.json` | Matriz por codigos antes y despues |
| `comprobaciones.sql` | Consultas de verificacion y la preparacion/restauracion de E06 |

| Operacion | Variables |
|---|---|
| PuntoDePartida (E01) | `e01_punto_de_partida.json` |
| ExplorarCatalogo / CatalogoCompleto / CatalogoRecursoInexistente (E02) | `e02_explorar_catalogo.json`, `e02_catalogo_completo.json`, `e02_catalogo_payments.json` |
| RevisarConfiguracion (E03, E06) | `e03_revisar_s1.json`, `e06_*.json` |
| AplicarConfiguracion (E04, E05, E06, E08, E09) | `e04_aplicar_s1.json`, `e05_aplicar_s0.json`, `e05_aplicar_s1.json`, `e06_*.json`, `e08_lista_vacia.json`, `e09_restaurar_s0.json` |
| ConsultarCuentas / RegistrarMovimiento (E10) | `e10_consultar_cuentas.json`, `e10_registrar_movimiento.json` |

Los ids de las variables son los de una base nueva preparada con `pruebas/actividad4.py` (Ana = 1, CAPTURISTA = 3, permisos 1 a 10).

Pruebas (base nueva y servidor arriba):

```
python pruebas/actividad4.py      # prepara empresa y personas
python pruebas/actividad5.py      # E01-E06, E08 (sin reinicio), E09, E10 -> pruebas/resultados_actividad5.json
docker compose exec api python -m unittest -v tests.test_e07_rollback   # E07
```

E08 con reinicio: aplicar `e08_lista_vacia.json`, `docker compose restart api` y revisar que CAPTURISTA siga con cero relaciones activas; luego restaurar con `e09_restaurar_s0.json`.

## Actividad 6 - Control de acceso segun el rol

`login(input: {email, password})` revisa el hash y, si coincide, firma un JWT HS256 de 30 minutos con solo `companyUserId`, `companyId` (copiado de la membresia) y `exp`. Regresa `AuthPayload { token tokenType user }`; `tokenType` es `"bearer"`. Si la persona tiene membresia en varias empresas se manda tambien `companyId` y se obtiene un token por empresa.

El secreto se lee de la variable de ambiente `JWT_SECRET` (ver `.env.example`); no esta en el codigo ni en el repo. Al validar solo se acepta HS256.

Las rutas ya no reciben `actorCompanyUserId`. Cada una llama `leer_actor` (`auth.py`): revisa `Authorization: Bearer ...`, la firma, `exp`, que la membresia exista y este activa y que sea de la empresa del token. Despues sigue `exigir_permiso` con el mismo permiso de antes. El rol no va en el token: se lee en MySQL en cada peticion.

| Ruta | Permiso |
|---|---|
| companyUsers, createCompanyUser, deactivateCompanyUser | company.users.read / company.users.write |
| accounts, createAccount | accounts.read, accounts.write |
| concepts, createConcept, assignConceptToAccount | concepts.read, concepts.write |
| transactions, createTransaction | transactions.read, transactions.write |
| permissionCatalog, previewRolePermissions | roles.read |
| setRolePermissions, assignRole, assignPermissionToRole, removePermissionFromRole | roles.write |

`login`, `createCompany` y el primer `createCompanyAdmin` no piden token.

En GraphiQL: ejecutar `login`, copiar el token y en HTTP headers poner

```
{"Authorization": "Bearer TOKEN_QUE_DEVOLVIO_LOGIN"}
```

Pruebas (servidor arriba; crean su propia empresa, se pueden repetir):

```
python pruebas/actividad6.py           # L1, L2 y casos C1-C10 -> pruebas/resultados_actividad6.json
python pruebas/ver_token.py TOKEN      # muestra solo los datos legibles del token
```

`pruebas/jwt_lab.py` tiene las ayudas de las pruebas (peticiones con encabezado, token alterado y token vencido firmado con el `JWT_SECRET` del laboratorio).

Nota: `pruebas/actividad4.py`, `pruebas/actividad5.py` y `actividad5/operaciones.graphql` usan `actorCompanyUserId` y corresponden al estado del proyecto en esas actividades; desde la 6 ese argumento ya no existe.

## Actividad 7 - Balances por cuenta y balance general

Integrantes: Roberto Balmes Solis, David Romero

### Que se agrego

- `createTransaction` acepta `transactionDate` opcional (DateTime con zona, por ejemplo `2026-10-27T12:00:00Z`). Se normaliza a UTC; si no viene se usa la hora del servidor. `capturedAt` siempre lo pone el servidor. `Transaction` expone `transactionDate`, `capturedAt` e `isActive`.
- El monto se valida en Python con `Decimal`: positivo, finito, con dos decimales como maximo (no se redondea) y que quepa en `Numeric(12, 2)`. Los importes se devuelven con el escalar `Decimal` como texto con dos decimales (`"1800.00"`).
- `balances.py` calcula los balances con una sola consulta agregada: parte de `accounts`, hace `LEFT JOIN` a `transactions` con los filtros del movimiento en el `ON` (activo, de la misma empresa, `transaction_date < fin`) y usa `SUM(CASE ...)` para saldo inicial, ingresos y egresos. Asi una cuenta sin movimientos sale con ceros. No se une a `account_concepts`, para no duplicar importes. El general suma en Python las mismas filas del detalle.
- Queries `accountBalance(accountId, fromDate, toDate)` y `generalBalance(fromDate, toDate)`. Las dos validan el token, piden `accounts.read` y `transactions.read` y toman `companyId` de la membresia del token. Una cuenta ajena y una inexistente responden igual: `Cuenta no disponible`.
- Periodo: `fromDate` y `toDate` son dias completos en UTC. Saldo inicial: `transaction_date < fromDate 00:00`. Periodo: `>= fromDate 00:00` y `< (toDate + 1 dia) 00:00`. `fromDate > toDate` da error.
- Se suma por `transaction_date`, nunca por `captured_at` ni `created_at`. Los movimientos inactivos no cuentan. Las cuentas desactivadas siguen en el balance con `isActive: false`.
- Todas las cantidades son MXN (`currency: "MXN"`); el proyecto no tiene campo de moneda.
- Consultar no guarda nada: no hay tabla de balances. La columna `accounts.balance` de las actividades anteriores se conserva por compatibilidad, pero los balances no la usan.

### Migracion

`main.py` agrega al arrancar, si faltan, las columnas `transaction_date`, `captured_at` e `is_active` en `transactions` y el indice `(account_id, transaction_date)`. Las filas previas toman `created_at` como fecha de operacion y de captura. Las fechas se guardan sin zona y por convencion son UTC. SQL equivalente: `migraciones/002_transaction_dates.sql`.

### Preparar datos y probar

Con el servidor arriba (`docker compose up --build`):

```
python pruebas/actividad7_datos.py          # crea la empresa con Banco, Caja y Ahorro y escribe actividad7/variables/*.json
python -m unittest -v tests.test_balances    # B01, B04, B06 y B12 automatizados (solo biblioteca estandar)
python pruebas/actividad7.py                 # B01 a B15 -> actividad7/evidencias.md y pruebas/resultados_actividad7.json
```

`pruebas/actividad7.py` usa SQL para B07 y B08; si MySQL no esta en el puerto 3307 del equipo, cambiar `MYSQL_CMD`, por ejemplo:

```
MYSQL_CMD="docker compose exec -T mysql mysql -uingresos -pingresos ingresos" python pruebas/actividad7.py
```

Cada caso adicional usa su propia empresa, asi el conjunto de referencia no cambia; B07, B08 y B14 restauran el estado al terminar. La preparacion y la restauracion manual estan en `actividad7/preparacion.sql`. Para empezar de cero: `docker compose down -v`.

### Archivos en `actividad7/`

| Archivo | Que es |
|---|---|
| `operaciones.graphql` | `Entrar`, `BalanceDeUnaCuenta`, `BalanceDeLaEmpresa`, `RegistrarConFecha` |
| `variables/` | `entrar.json`, `balance_banco.json`, `balance_caja.json`, `balance_ahorro.json`, `balance_banco_28.json`, `balance_general.json`, `captura_con_fecha.json` (este agrega un egreso a Banco: usarlo despues de guardar la evidencia de referencia) |
| `preparacion.sql` | Preparacion y restauracion de B07/B08 y una comprobacion manual en SQL |
| `evidencias.md` | B01 a B15 con el resultado obtenido y la regla comprobada |
| `salida_tests.txt` | Salida de `python -m unittest -v tests.test_balances` |
| `explicacion.md` | Saldo inicial, profit, saldo final y numeros rojos con los numeros de Banco y Caja |

### Tabla de referencia (26 al 30 de octubre de 2026)

| Cuenta | Saldo inicial | Ingresos | Egresos | Profit | Saldo final | En rojo |
|---|---|---|---|---|---|---|
| Banco | 1,000.00 | 3,000.00 | 2,200.00 | 800.00 | 1,800.00 | No |
| Caja | 0.00 | 500.00 | 700.00 | -200.00 | -200.00 | Si |
| Ahorro | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | No |
| General | 1,000.00 | 3,500.00 | 2,900.00 | 600.00 | 1,600.00 | No (`accountsInRed: 1`) |
