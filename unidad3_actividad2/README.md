# Unidad III · Actividad 2 · Dashboard administrativo

Equipo (el mismo del Sistema General de Ingresos): **Roberto Balmes Solís** y **David Romero**

Se monta sobre el dashboard financiero de la Actividad 1: misma aplicación, mismo login y mismo API GraphQL.
El código del cliente está en `dashboard/` (no es un segundo proyecto).

## Cómo se entra a la administración

```bash
cp .env.example .env                       # solo la primera vez; poner JWT_SECRET
docker compose up --build                  # MySQL en 3307, API en 8000 (aplica la migración 003 al arrancar)
python pruebas/u3_actividad1_datos.py      # datos de demostración, si la base está vacía
```

1. Abrir **http://localhost:8000/dashboard/** e iniciar sesión.
2. En el menú de la izquierda, bajo **Dashboard administrativo**, elegir **Usuarios**, **Cuentas** o **Conceptos**.
   **Dashboard financiero** sigue en el mismo menú. Cada sección tiene su propia dirección:
   `#/financiero`, `#/admin/usuarios`, `#/admin/cuentas`, `#/admin/conceptos`.
3. **Cerrar sesión** borra el token y vuelve al login. Si el token falta o el API lo rechaza, también se vuelve al login.

## Roles con los que probamos (contraseña de laboratorio `demo123`)

| Correo | Rol | Qué ve en la administración |
|---|---|---|
| `roberto.demo@ingresos.test` | **ADMINISTRADOR**: el rol que usamos para probar la escritura | Las tres tablas y los botones Nuevo usuario, Desactivar, Nueva cuenta, Nuevo concepto, Asignar y Quitar |
| `david.demo@ingresos.test` | CONSULTA (`company.users.read`, `accounts.read`, `concepts.read`) | Las tres tablas, **sin** botones de alta ni de baja |
| `invitado.demo@ingresos.test` | sin rol | “Acceso denegado” en cada sección |

Los botones se dibujan según `mySession.permissions` (los permisos del rol de la sesión). El servidor sigue
validando cada mutation con `exigir_permiso`; ocultar el botón no es la seguridad, solo evita una acción que fallaría.

## Archivos de esta entrega

| Entregable | Dónde |
|---|---|
| `createTransaction` idempotente y tabla de llaves | `schema.py` (`create_transaction`, `huella_movimiento`, `buscar_llave`), `models.py` (`IdempotencyKeyModel`), `migraciones/003_admin_dashboard.sql` |
| Explicación de la idempotencia | `unidad3_actividad2/idempotencia.md` |
| Pruebas automatizadas de la idempotencia | `tests/test_idempotencia.py` (salida en `salida_tests_idempotencia.txt`) |
| Comprobación en MySQL | `comprobacion_mysql.sql` y `salida_mysql_idempotencia.txt` |
| Cliente con las tres secciones | `dashboard/index.html`, `dashboard/admin.js`, `dashboard/styles.css` |
| Evidencias con capturas | `unidad3_actividad2/evidencias.md` y `unidad3_actividad2/capturas/` |
| Guion de la demostración final | `unidad3_actividad2/guion_demo.md` |
| Boceto | No cambió: seguimos el wireframe de la figura 9 (menú a la izquierda, título, acción principal, búsqueda/filtros y tabla) |

## Cambios al backend

No hay un modelo nuevo de negocio; se completó lo que la pantalla necesitaba leer:

- **Idempotencia:** tabla `idempotency_keys` con índice único `(company_id, operation, idem_key)`; `createTransaction`
  recibe `idempotencyKey`. La llave y el movimiento entran en el mismo `COMMIT`.
- **Cuentas:** columnas `account_type` (CASH, DEBIT, CREDIT, SAVINGS, INVESTMENT, WALLET, OTHER), `bank_name`, `clabe` y
  `description`. El API devuelve `clabeMasked` (`•••• 7893`): la CLABE completa no sale en ninguna consulta.
  Las cuentas viejas Caja/Banco/Ahorro tomaron CASH/DEBIT/SAVINGS en la migración; las demás quedaron en OTHER.
- **Conceptos:** columna `description`.
- **Queries:** `accounts(activeOnly)`, `concepts(activeOnly)`, `accountConcepts(accountId, activeOnly)` (nueva) y
  `mySession.permissions` (nueva).
- **Mutations:** `removeConceptFromAccount` (nueva, baja lógica de la relación). `assignConceptToAccount` reactiva la
  misma fila si la pareja se había quitado. `createAccount`/`createConcept` aceptan los campos nuevos y validan nombre
  obligatorio y CLABE de 18 dígitos. `createCompanyUser` valida formato de correo y una contraseña de 6 caracteres o más.

Nombres que usamos de nuestro esquema en lugar de los del ejemplo del PDF: `type` en lugar de `conceptType`
(el campo ya existía así desde el Parcial I), y `companyUsers`/`accounts`/`concepts` sin `companyId`, porque la
empresa sale del token, no de un argumento que el cliente pueda cambiar.
