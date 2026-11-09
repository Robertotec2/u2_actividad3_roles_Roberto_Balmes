# Guion de la demostración final del Parcial III

Equipo: Roberto Balmes Solís y David Romero · Duración aproximada: 4 minutos

**Antes de empezar:** `docker compose up --build`, `python pruebas/u3_actividad1_datos.py` (si la base está
vacía) y abrir http://localhost:8000/dashboard/ y, en otra pestaña, http://localhost:8000/graphql.

1. **Login (Roberto).** Entrar con `roberto.demo@ingresos.test` / `demo123`. Explicar que se llama a la mutación
   `login` y que el token viaja en `Authorization: Bearer` en cada consulta; no se guarda en el repositorio.
2. **Dashboard (Roberto).** Mostrar el encabezado (empresa, MXN, usuario y rol) y elegir **26–30 oct 2026**.
   Leer los totales: inicial 1,000.00, ingresos 3,500.00, egresos 2,900.00, profit 600.00, saldo final 1,600.00.
3. **Mismo dato en GraphiQL (David).** Ejecutar `generalBalance` con las mismas fechas y señalar que
   `closingBalance` es `"1600.00"`: el dashboard no calcula, solo lee.
4. **Cuenta en rojo con total positivo (David).** Señalar el bloque de riesgo: el general **no** está en rojo, pero
   hay **1 cuenta en rojo (Caja, −200.00)**, resaltada en la tabla.
5. **Cambio de fechas (Roberto).** Poner del 28 al 28: Banco tiene profit −1,000.00 (naranja) y saldo final
   1,800.00, por eso no está en rojo. Luego invertir las fechas para mostrar el aviso sin llamar al API.
6. **Permisos (David).** Cerrar sesión y entrar con `invitado.demo@ingresos.test`: aparece **Acceso denegado** sin
   números. Para cerrar, entrar como `david.demo@ingresos.test` (CONSULTA) y ver que sí puede leer.

Preguntas que cualquiera del equipo puede contestar: de qué campo sale cada tarjeta (tabla en
`dashboard/README.md`), por qué no se usa `float` y qué pasa cuando el token vence.
