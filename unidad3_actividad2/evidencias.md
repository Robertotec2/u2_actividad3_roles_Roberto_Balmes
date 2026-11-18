# Evidencias · Unidad III · Actividad 2 · Dashboard administrativo

Integrantes: Roberto Balmes Solís, David Romero

Capturas tomadas el 18 de noviembre de 2026 con el backend en Docker (`docker compose up --build`), los datos de la
empresa de demostración **Papelería El Cuaderno** (empresa #1) y el dashboard en http://localhost:8000/dashboard/.

## Parte 1 · Idempotencia (antes de las pantallas)

### 1. Primer envío de `createTransaction` con `idempotencyKey`

Renta de 100.00 en Banco con la llave `renta-nov-2026-7f3c9a12-…`. Se crea el movimiento **64**.

![Primer envío](capturas/01_idempotencia_primer_envio.png)

### 2. Reintento con la misma llave → mismo movimiento

La misma mutación con la misma llave devuelve otra vez el **id 64** con el mismo `capturedAt`: no hubo otro `INSERT`.

![Reintento con la misma llave](capturas/02_idempotencia_reintento_misma_llave.png)

### 3. Otra llave, mismo monto → otro movimiento

Con una llave nueva se crea el movimiento **65**, aunque el monto sea igual: dos rentas de 100 pueden ser legítimas.

![Otra llave](capturas/03_idempotencia_otra_llave_otro_movimiento.png)

### 4. Misma llave con otros datos → error

La primera llave con monto 250.00 responde `Esa idempotencyKey ya se uso con otros datos` y no inserta nada.

![Misma llave, otros datos](capturas/04_idempotencia_misma_llave_otros_datos.png)

### En MySQL hay una sola fila por llave

Salida de `comprobacion_mysql.sql` (`salida_mysql_idempotencia.txt`):

```
| idem_key                                            | movimientos |
| renta-nov-2026-7f3c9a12-4b1e-4d2a-9c55-1a2b3c4d5e6f |           1 |
| renta-nov-2026-segundo-pago-b81d4e70-2c9f-4a35      |           1 |
```

Pruebas automatizadas (`salida_tests_idempotencia.txt`): 6 OK, incluida la de 5 envíos simultáneos con la misma llave.

## Parte 2 · Dashboard administrativo (usuario Roberto Balmes, rol ADMINISTRADOR)

### 5. Una sola aplicación: el menú distingue el financiero del administrativo

El dashboard financiero de la Actividad 1 se conserva; se le agregó el menú. En noviembre ya aparecen los dos egresos
de renta de la prueba de idempotencia (Egresos $200.00, no $300.00).

![Menú y dashboard financiero](capturas/05_menu_dashboard_financiero.png)

### 6. Usuarios (`companyUsers`)

Coincide con `companyUsers` en GraphiQL. Conteos de personas (sin MXN): activos, administrador principal (1) e inactivos.
El rol es de solo lectura; Invitado aparece “Sin rol”. El administrador principal no tiene botón Desactivar.

![Usuarios](capturas/06_usuarios.png)

### 7–8. Alta de usuario

El formulario pide nombre, correo y contraseña (no pide `isAdmin`). Al guardar, la tabla se vuelve a consultar.

![Formulario de alta](capturas/07_usuarios_formulario_alta.png)
![Alta correcta](capturas/08_usuarios_alta_correcta.png)

### 9. Error: correo duplicado

El mensaje del servidor se lee en la pantalla.

![Correo duplicado](capturas/09_error_correo_duplicado.png)

### 10–11. Baja lógica

La confirmación dice que la persona deja de operar y que el historial se conserva. La fila sigue, en gris, con estado
**Inactivo**; el conteo de inactivos pasa a 1.

![Confirmar desactivar](capturas/10_usuarios_confirmar_desactivar.png)
![Baja lógica](capturas/11_usuarios_baja_logica.png)

### 12. GraphiQL confirma `isActive: false`

![GraphiQL companyUsers](capturas/19_graphiql_companyUsers_isActive_false.png)

### 13–15. Cuentas (`accounts`)

Alta de **BBVA Empresarial** (Débito, BBVA, CLABE de 18 dígitos). En la tabla el tipo sale con su etiqueta (Efectivo,
Débito, Ahorro…) y la referencia enmascarada (`CLABE •••• 7893`); Caja no tiene banco. Filtros: Todas, por tipo y Solo activas.

![Formulario de cuenta](capturas/12_cuentas_formulario_alta.png)
![Cuentas](capturas/13_cuentas.png)
![Filtro Débito](capturas/14_cuentas_filtro_debito.png)

### 16–19. Conceptos (`concepts` + `accountConcepts`)

Se creó **Comisiones bancarias** (Egreso) y se asignó a BBVA Empresarial. Asignarlo otra vez muestra el error de
duplicado. Al quitarlo, el concepto sigue en el catálogo y ya no aparece entre los permitidos de la cuenta.

![Concepto asignado](capturas/15_conceptos_asignado.png)
![Error concepto ya asignado](capturas/16_error_concepto_ya_asignado.png)
![Quitado, sigue en el catálogo](capturas/17_conceptos_quitado_sigue_en_catalogo.png)
![Banco, filtro Egreso](capturas/18_conceptos_banco_filtro_egreso.png)

## Permisos

### 20–22. Usuario de solo consulta (David Romero, CONSULTA)

Ve las tres tablas y no ve Nuevo usuario, Desactivar, Nueva cuenta, Nuevo concepto, Asignar ni Quitar.

![CONSULTA usuarios](capturas/20_consulta_usuarios_sin_botones.png)
![CONSULTA cuentas](capturas/21_consulta_cuentas_sin_botones.png)
![CONSULTA conceptos](capturas/22_consulta_conceptos_sin_asignar_ni_quitar.png)

### 23. Usuario sin rol

`invitado.demo@ingresos.test` ve “Acceso denegado” y no una tabla a medias.

![Sin rol](capturas/23_sin_rol_acceso_denegado.png)

### 24. Celular (390 px)

El menú pasa arriba y las columnas se apilan; la página no tiene scroll horizontal (la tabla del catálogo se desplaza
dentro de su recuadro).

![Celular](capturas/24_conceptos_celular.png)

## Lista de comprobación del PDF

| # | Comprobación | Resultado | Evidencia |
|---|---|---|---|
| I-1 | Misma `idempotencyKey` dos veces → mismo movimiento | ✅ id 64 y 64 | 01, 02 |
| I-2 | Otra llave, mismo monto → segundo movimiento | ✅ id 65 | 03 |
| I-3 | En MySQL una sola fila para la primera llave | ✅ | `salida_mysql_idempotencia.txt` |
| 1 | Login de la actividad 1 y abrir Dashboard administrativo | ✅ | 05, 06 |
| 2 | Tabla de usuarios = `companyUsers` en GraphiQL | ✅ | 06, 19 |
| 3 | Crear usuario; el correo duplicado se rechaza en pantalla | ✅ | 08, 09 |
| 4 | Desactivarlo; la fila sigue inactiva y GraphiQL muestra `isActive: false` | ✅ | 11, 19 |
| 5 | Crear una cuenta | ✅ BBVA Empresarial | 13 |
| 6 | Crear concepto de egreso, asignarlo; asignarlo otra vez da error | ✅ | 15, 16 |
| 7 | Quitarlo; sigue en el catálogo | ✅ | 17 |
| 8 | Usuario de solo consulta ve las tablas sin botones de alta | ✅ | 20–22 |
| — | La contraseña no aparece en ninguna tabla ni consulta | ✅ solo existe en el formulario de alta | 07 |
| — | Cerrar sesión vuelve al login | ✅ “Cerraste sesión.” | — |
