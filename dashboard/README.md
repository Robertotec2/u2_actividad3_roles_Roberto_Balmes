# Dashboard financiero (Unidad III · Actividad 1)

Integrantes: **Roberto Balmes Solís** y **David Romero**

Cliente web del Sistema General de Ingresos. Inicia sesión con la mutación `login`, guarda el token en
`sessionStorage` y consulta `generalBalance` con `Authorization: Bearer`. No calcula nada: solo formatea
lo que devuelve el API.

## Opción elegida

**Página web sencilla (HTML + CSS + JavaScript)** sin dependencias ni `node_modules`. FastAPI la sirve en
`/dashboard/` (mismo origen que `/graphql`), así que no hace falta CORS.

| Archivo | Qué hace |
|---|---|
| `index.html` | Pantallas de login y dashboard; cada bloque del boceto está marcado con un comentario |
| `styles.css` | Estilos (jerarquía visual, rojo para saldos negativos, naranja para profit negativo) |
| `app.js` | Login, consulta `IndicadoresEmpresa`, formato MXN y manejo de errores |
| `config.js` | URL del API (`/graphql` por defecto) |

## Cómo levantarlo

Desde la raíz del repositorio:

```bash
cp .env.example .env                                     # solo la primera vez
python -c "import secrets; print(secrets.token_hex(32))" # pegar el valor en JWT_SECRET de .env
docker compose up --build                                # MySQL en 3307, API en 8000
python pruebas/u3_actividad1_datos.py                    # datos de demostración (una sola vez)
```

Abrir **http://localhost:8000/dashboard/** (http://localhost:8000/ redirige ahí). GraphiQL sigue en
http://localhost:8000/graphql.

### Servirlo en otro puerto (opcional)

```bash
# 1) en .env o en el ambiente del API
CORS_ORIGINS=http://localhost:5173
# 2) en dashboard/config.js
graphqlUrl: "http://localhost:8000/graphql"
# 3) servir la carpeta
python -m http.server 5173 --directory dashboard
```

`compose.yaml` ya pasa `CORS_ORIGINS` desde `.env` al servicio `api`.

## Usuarios de prueba (contraseña de laboratorio `demo123`)

| Correo | Nombre | Rol | Qué ve |
|---|---|---|---|
| `roberto.demo@ingresos.test` | Roberto Balmes | ADMINISTRADOR | Dashboard completo |
| `david.demo@ingresos.test` | David Romero | CONSULTA | Dashboard completo (solo lectura) |
| `invitado.demo@ingresos.test` | Invitado Sin Rol | sin rol | “Acceso denegado”, sin cifras |

Período de demostración: **2026-10-26 al 2026-10-30** (botón “26–30 oct 2026”).

## Flujo

1. Login → `mutation IniciarSesion` → se guarda el token en `sessionStorage` (nunca en el repositorio).
2. `query MiSesion` (`mySession`) → nombre de la empresa, RFC, usuario y rol para el encabezado.
3. `query IndicadoresEmpresa` (`generalBalance`) con el período → se pintan indicadores, riesgo y detalle.
4. Cambiar una fecha, un atajo o pulsar **Actualizar** → se repite el paso 3. Si llega una respuesta de una
   petición anterior se ignora, para no mezclar un período viejo con etiquetas nuevas. La etiqueta del período
   se toma de `fromDate`/`toDate` de la respuesta.
5. **Cerrar sesión** → se borra el token y se vuelve al login.

## Relación pantalla ↔ GraphQL

| En pantalla | Campo |
|---|---|
| Saldo final general (tarjeta grande) | `closingBalance` |
| Saldo inicial | `openingBalance` |
| Ingresos | `totalIncome` |
| Egresos | `totalExpense` |
| Profit | `profit` |
| ¿Saldo general en rojo? | `isInRed` |
| Cuentas en rojo (y sus nombres) | `accountsInRed` (los nombres son las filas de `accounts` con `isInRed: true`) |
| Tabla “Detalle por cuenta” | `accounts { accountName isActive openingBalance totalIncome totalExpense profit closingBalance isInRed }` |
| Período consultado · MXN | `fromDate`, `toDate`, `currency` |

## Reglas que respeta

- **Sin float:** el servidor manda `"1800.00"` como texto y el cliente solo le pone `$`, comas y el signo `−`.
- **Fechas:** si `fromDate > toDate` no se llama al API y se muestra el aviso.
- **Token inválido, vencido o ausente:** vuelve al login con “Tu sesión expiró o el token no es válido”. También
  cierra sesión sola al llegar el `exp` del token (30 min).
- **Sin permiso de lectura** (`accounts.read` + `transactions.read`): panel “Acceso denegado” sin números.
- **Estados vacíos:** “La empresa todavía no tiene cuentas” o “No hubo movimientos entre … y …”.
- **Números rojos:** saldo negativo en rojo con etiqueta “En rojo”; un profit negativo se pinta en naranja y no
  marca la cuenta como en rojo si su saldo final sigue positivo.
- No hay `companyId` libre ni `actorCompanyUserId`: la empresa y la identidad salen del token.
