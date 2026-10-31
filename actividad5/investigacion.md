# Investigacion - Actividad 5

Integrantes: Roberto Balmes Solis, David Romero

## 1. Autenticacion, autorizacion y configuracion de permisos

Son tres preguntas distintas. **Autenticar** es comprobar quien es la persona: en nuestro sistema eso pasa en
`login`, cuando se vuelve a calcular el hash PBKDF2 de lo que escribio y se compara con el que esta en `users`.
**Autorizar** es decidir si esta peticion puede hacer esta accion: `exigir_permiso` busca el rol activo de la
membresia y revisa si ese rol tiene, por ejemplo, `accounts.write` antes de que `createAccount` guarde la cuenta.
**Configurar permisos** es decidir que acciones tiene cada rol; es lo que hace `setRolePermissions` cuando le deja
a CAPTURISTA la lista S1. Configurar no dice quien llama en este momento.

`actorCompanyUserId` no comprueba identidad porque es solo un numero que escribe el cliente. Si en GraphiQL pongo
`"actor": "1"` el servidor cree que soy Ana aunque no sepa su contrasena. Sirve en el laboratorio para practicar
la autorizacion, pero para autenticar el id tiene que salir de algo que el servidor firmo y valida en cada
peticion (un token), que es lo del tema 2.

Fuente: GraphQL, *Authorization* (graphql.org/learn/authorization). Ahi explican que la logica de autorizacion
va en la capa de negocio y no en el esquema; por eso dejamos la decision en Python dentro de cada resolver.

## 2. Variables, alias y fragmentos para pruebas repetibles

Las **variables** separan los datos del texto de la operacion. Asi `AplicarConfiguracion` es siempre el mismo
documento y solo cambia el JSON: `e04_aplicar_s1.json` o `e05_aplicar_s0.json`. Si cambia el id de Ana en otra
base, solo se edita el JSON. Los **alias** permiten pedir el mismo campo dos veces con argumentos distintos y que
la respuesta tenga claves diferentes. Los **fragmentos** evitan repetir la seleccion `id code name`.

Operacion propia que usa los tres:

```graphql
query CompararGrupos($actor: ID!) {
  lectura: permissionCatalog(resource: CONCEPTS, actorCompanyUserId: $actor) { ...DatosPermiso }
  configuracion: permissionCatalog(resource: ROLES, actorCompanyUserId: $actor) { ...DatosPermiso }
}
fragment DatosPermiso on Permission { id code name }
```

La respuesta trae `lectura` y `configuracion`, cada una con dos permisos. El alias solo cambia el nombre de la
clave, el servidor ejecuta dos veces el mismo resolver.

Fuente: GraphQL, *Queries* (graphql.org/learn/queries).

## 3. Que valida un enum o un input y que se valida en Python

GraphQL valida la **forma**: que `resource` sea uno de los cinco valores de `PermissionResource` (por eso
`PAYMENTS` da error antes de ejecutar el resolver), que `SetRolePermissionsInput` traiga `roleId` y
`permissionIds`, y que ninguno de los elementos de la lista sea null. En Strawberry el enum se declara con
`@strawberry.enum` y el input con `@strawberry.input`, y Strawberry genera el SDL a partir de las clases.

Lo que GraphQL no sabe es lo que esta en MySQL. En `configuracion.py` validamos que el rol exista y este activo,
que no sea ADMINISTRADOR, que cada id sea un numero, que exista, que el permiso este activo y que no venga
repetido (`["3", 3]` es repeticion porque el tipo ID acepta las dos formas).

`[ID!]!` acepta `[]` porque el `!` de afuera solo dice que la lista no puede ser null y el de adentro que sus
elementos no pueden ser null. Una lista vacia no tiene elementos null, asi que es valida. En nuestro caso
significa "dejar a este rol sin permisos" (caso E08).

Fuentes: Strawberry, *Enums* (strawberry.rocks/docs/types/enums) e *Input types*
(strawberry.rocks/docs/types/input-types).

## 4. Atomicidad e idempotencia

**Atomicidad** es que todos los cambios de una lista se confirman juntos o no se confirma ninguno. En
`aplicar_lista` las activaciones y desactivaciones se hacen en la misma sesion, se manda `flush` y hay un solo
`commit` al final. Si algo falla antes, la sesion se cierra sin commit y SQLAlchemy hace rollback; el test E07
lo comprueba provocando un error justo despues del flush.

**Idempotencia** es que repetir la misma peticion deja el mismo estado. Si CAPTURISTA ya tiene S1 y se manda
S1 otra vez, el plan sale sin altas ni bajas, no se escribe nada y regresa `changed: false`.

Mandar varias mutaciones en una sola peticion GraphQL no da rollback conjunto porque cada resolver abre su
propia sesion y hace su propio commit. GraphQL ejecuta los campos de mutation en orden, pero no sabe nada de
transacciones de base de datos; si la tercera falla, las dos primeras ya quedaron guardadas.

Fuentes: SQLAlchemy, *Transactions and Connection Management*
(docs.sqlalchemy.org/en/20/orm/session_transaction.html); GraphQL, *Mutations* (graphql.org/learn/mutations).

## Referencias

| Titulo | URL | Consulta |
|---|---|---|
| Authorization - GraphQL | https://graphql.org/learn/authorization/ | 20/10/2026 |
| Queries - GraphQL | https://graphql.org/learn/queries/ | 20/10/2026 |
| Mutations - GraphQL | https://graphql.org/learn/mutations/ | 20/10/2026 |
| Enums - Strawberry | https://strawberry.rocks/docs/types/enums | 20/10/2026 |
| Input types - Strawberry | https://strawberry.rocks/docs/types/input-types | 20/10/2026 |
| Transactions and Connection Management - SQLAlchemy | https://docs.sqlalchemy.org/en/20/orm/session_transaction.html | 20/10/2026 |
