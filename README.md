# Sistema General de Ingresos - Roles y control de acceso

Unidad 2 Actividad 3. Se agregaron roles, permisos y la matriz de permisos por rol encima del sistema de empresas, usuarios, cuentas, conceptos y movimientos.

## Como correrlo

```
docker compose up --build
```

Luego entrar a http://localhost:8000/graphql

Sin docker (con MySQL local):

```
pip install -r requirements.txt
set DATABASE_URL=mysql+pymysql://ingresos:ingresos@localhost:3306/ingresos
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
