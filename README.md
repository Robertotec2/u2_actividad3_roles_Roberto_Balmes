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
