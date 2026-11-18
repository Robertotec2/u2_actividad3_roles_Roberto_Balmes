# Guion de la demostración final del Parcial III (backend + vista financiera + vista administrativa)

Equipo: Roberto Balmes Solís y David Romero · Duración aproximada: 7 minutos

**Antes de empezar:** `docker compose up --build`, `python pruebas/u3_actividad1_datos.py` (si la base está vacía),
abrir http://localhost:8000/dashboard/ y, en otra pestaña, http://localhost:8000/graphql.

1. **Login y dashboard financiero (Roberto).** Entrar con `roberto.demo@ingresos.test` / `demo123`, elegir
   **26–30 oct 2026** y leer los totales (inicial 1,000.00 · final 1,600.00 · Caja en rojo). Explicar el menú: misma
   aplicación, dos dashboards.
2. **Idempotencia (David, en GraphiQL).** Ejecutar `createTransaction` con una `idempotencyKey` nueva, repetirlo y
   señalar que el `id` es el mismo. Cambiar la llave: sale otro `id`. Explicar que la llave y el movimiento se
   confirman en el mismo `COMMIT` de MySQL y por qué no se usa Redis.
3. **Usuarios (Roberto).** Mostrar los conteos y la columna Rol. Crear un usuario; intentar el mismo correo y leer el
   error en pantalla. Desactivarlo: la fila queda inactiva. David muestra `isActive: false` en GraphiQL.
4. **Cuentas (Roberto).** Crear una cuenta de débito con banco y CLABE; señalar que la CLABE sale enmascarada.
5. **Conceptos (David).** Crear un concepto de egreso, asignarlo a la cuenta nueva, asignarlo otra vez (error de
   duplicado) y quitarlo: sigue en el catálogo.
6. **Permisos (David).** Cerrar sesión, entrar como `david.demo@ingresos.test` (CONSULTA): ve las tablas sin botones.
   Entrar como `invitado.demo@ingresos.test`: “Acceso denegado”.

Preguntas que cualquiera del equipo puede contestar: de qué query sale cada tabla (`companyUsers`, `accounts`,
`concepts`, `accountConcepts`), por qué ocultar el botón no es la seguridad (el servidor valida con `exigir_permiso`),
y qué diferencia hay entre idempotencia y rate limiting.
