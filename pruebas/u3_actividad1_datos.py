"""Unidad 3 Actividad 1: datos de demostracion del dashboard financiero.

Crea (una sola vez) la empresa de demostracion con Banco, Caja y Ahorro y los mismos movimientos
de referencia de la Actividad 7 de la Unidad 2, con usuarios de correo fijo para el login:

    roberto.demo@ingresos.test / demo123   ADMINISTRADOR (ve todo)
    david.demo@ingresos.test   / demo123   CONSULTA (solo lectura, tambien ve el dashboard)
    invitado.demo@ingresos.test / demo123  sin rol (el dashboard muestra "acceso denegado")

Si el administrador ya puede iniciar sesion no se crea nada otra vez. Uso (servidor arriba):

    python pruebas/u3_actividad1_datos.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from actividad7_datos import CONCEPTOS, MOVIMIENTOS, PERMITIDOS, crear_concepto, crear_cuenta, mover, permitir  # noqa: E402
from jwt_lab import dato, gql  # noqa: E402

EMPRESA = "Papeleria El Cuaderno"
RFC = "PEC261026AB1"
CLAVE = "demo123"
ADMIN = ("Roberto Balmes", "roberto.demo@ingresos.test")
LECTOR = ("David Romero", "david.demo@ingresos.test")
SIN_ROL = ("Invitado Sin Rol", "invitado.demo@ingresos.test")

LOGIN = 'mutation($e: String!, $p: String!) { login(input: {email: $e, password: $p}) { token } }'


def entrar(email):
    r = gql(LOGIN, {"e": email, "p": CLAVE})
    return None if r.get("errors") else r["data"]["login"]["token"]


def preparar():
    token = entrar(ADMIN[1])
    if token:
        print("La empresa de demostracion ya existe; no se crea nada.")
        return

    empresa = dato('mutation($n: String!, $r: String!) { createCompany(input: {name: $n, rfc: $r}) { id } }',
                   "createCompany", variables={"n": EMPRESA, "r": RFC})["id"]
    dato('mutation($c: ID!, $n: String!, $e: String!, $p: String!) '
         '{ createCompanyAdmin(input: {companyId: $c, name: $n, email: $e, password: $p}) { id } }',
         "createCompanyAdmin", variables={"c": empresa, "n": ADMIN[0], "e": ADMIN[1], "p": CLAVE})
    token = entrar(ADMIN[1])

    cuentas = {n: crear_cuenta(token, n) for n in ("Banco", "Caja", "Ahorro")}
    conceptos = {n: crear_concepto(token, n, tipo) for n, tipo in CONCEPTOS}
    for cuenta, lista in PERMITIDOS.items():
        for c in lista:
            permitir(token, cuentas[cuenta], conceptos[c])
    for cuenta, fecha, concepto, monto, desc in MOVIMIENTOS:
        mover(token, cuentas[cuenta], conceptos[concepto], monto, fecha, desc)

    crear_usuario = ('mutation($n: String!, $e: String!, $p: String!) '
                     '{ createCompanyUser(input: {name: $n, email: $e, password: $p}) { id } }')
    lector = dato(crear_usuario, "createCompanyUser", token, {"n": LECTOR[0], "e": LECTOR[1], "p": CLAVE})["id"]
    dato(crear_usuario, "createCompanyUser", token, {"n": SIN_ROL[0], "e": SIN_ROL[1], "p": CLAVE})

    roles = {r["code"]: r["id"] for r in dato("{ roles { id code } }", "roles")}
    dato('mutation($u: ID!, $r: ID!) { assignRole(input: {companyUserId: $u, roleId: $r}) { id } }',
         "assignRole", token, {"u": lector, "r": roles["CONSULTA"]})

    print(f"Empresa {EMPRESA} creada con id {empresa}; cuentas {cuentas}")


if __name__ == "__main__":
    preparar()
    print("Usuarios (contrasena de laboratorio demo123):")
    for nombre, correo in (ADMIN, LECTOR, SIN_ROL):
        print(f"  {correo:32} {nombre}")
    print("Periodo de demostracion: 2026-10-26 al 2026-10-30")
