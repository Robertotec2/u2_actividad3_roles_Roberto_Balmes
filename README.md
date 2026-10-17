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
