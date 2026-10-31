"""Actividad 6: login con JWT y casos 1 a 9 (mas L1, L2 y C10).
Cada corrida crea su propia empresa, asi que se puede repetir sobre la misma base.

    python pruebas/actividad6.py [sufijo]
"""
import json
import os
import sys

from jwt_lab import gql, dato, error, sql, login, recortar, token_vencido, alterar

SALIDA = os.path.join(os.path.dirname(__file__), "resultados_actividad6.json")
resultados = []

CREAR_CUENTA = 'mutation($n: String!) { createAccount(input: {name: $n}) { id companyId } }'
CREAR_MOV = """mutation($a: ID!, $c: ID!, $m: Decimal!) {
  createTransaction(input: {accountId: $a, conceptId: $c, amount: $m}) { id capturedBy }
}"""


def caso(clave, token, ruta, ok, obtenido, regla):
    resultados.append({"caso": clave, "token": recortar(token) if token else None, "ruta": ruta,
                       "ok": bool(ok), "obtenido": obtenido, "regla": regla})
    print("OK   " if ok else "FALLA", clave, ruta, "-", obtenido)


def contar(tabla):
    return sql(f"SELECT COUNT(*) FROM {tabla}")


def main():
    n = sys.argv[1] if len(sys.argv) > 1 else "6"
    empresa = dato(f'mutation {{ createCompany(input: {{name: "Comercial del Sureste", rfc: "CSU2610{n:0>2}A6"}}) {{ id }} }}', "createCompany")["id"]
    otra = dato(f'mutation {{ createCompany(input: {{name: "Abarrotes Kanasin", rfc: "AKA2610{n:0>2}B6"}}) {{ id }} }}', "createCompany")["id"]
    dato(f'mutation {{ createCompanyAdmin(input: {{companyId: "{empresa}", name: "Ana", email: "ana{n}@a6.mx", password: "ana123"}}) {{ id }} }}', "createCompanyAdmin")
    dato(f'mutation {{ createCompanyAdmin(input: {{companyId: "{otra}", name: "Rosa", email: "rosa{n}@a6.mx", password: "rosa123"}}) {{ id }} }}', "createCompanyAdmin")
    t_ana = login(f"ana{n}@a6.mx", "ana123")
    t_rosa = login(f"rosa{n}@a6.mx", "rosa123")

    roles = {r["code"]: r["id"] for r in dato("{ roles { id code } }", "roles")}
    m, t = {}, {}
    for nombre, rol in [("Luis", "CONTADOR"), ("Maria", "CAPTURISTA"), ("Pedro", "CONSULTA")]:
        m[nombre] = dato(f'mutation {{ createCompanyUser(input: {{name: "{nombre}", email: "{nombre.lower()}{n}@a6.mx", password: "{nombre.lower()}123"}}) {{ id }} }}', "createCompanyUser", t_ana)["id"]
        dato(f'mutation {{ assignRole(input: {{companyUserId: "{m[nombre]}", roleId: "{roles[rol]}"}}) {{ id }} }}', "assignRole", t_ana)
        t[nombre] = login(f"{nombre.lower()}{n}@a6.mx", f"{nombre.lower()}123")

    cuenta = dato(CREAR_CUENTA, "createAccount", t["Luis"], {"n": "Caja general"})["id"]
    concepto = dato('mutation { createConcept(input: {name: "Venta de mostrador", type: INCOME}) { id } }', "createConcept", t["Luis"])["id"]
    dato(f'mutation {{ assignConceptToAccount(input: {{accountId: "{cuenta}", conceptId: "{concepto}"}}) {{ id }} }}', "assignConceptToAccount", t["Luis"])
    mov = {"a": cuenta, "c": concepto, "m": "150.00"}

    r = gql('mutation { login(input: {email: "maria%s@a6.mx", password: "maria123"}) { tokenType token user { name } } }' % n)
    tok = r["data"]["login"]["token"]
    import base64
    datos = json.loads(base64.urlsafe_b64decode(tok.split(".")[1] + "=="))
    cab = json.loads(base64.urlsafe_b64decode(tok.split(".")[0] + "=="))
    caso("L1", None, "login", r["data"]["login"]["tokenType"] == "bearer" and cab["alg"] == "HS256"
         and sorted(datos) == ["companyId", "companyUserId", "exp"] and str(datos["companyId"]) == empresa,
         f"Token {cab['alg']} con {sorted(datos)}; no trae contrasena, hash ni permisos",
         "El servidor firma el token solo despues de comprobar el hash; companyId sale de la membresia")

    r = gql('mutation { login(input: {email: "maria%s@a6.mx", password: "mal"}) { token } }' % n)
    caso("L2", None, "login", error(r) and r.get("data") is None, f"{error(r)}; data = {r.get('data')}",
         "Si el hash no coincide no se firma nada")

    antes = contar("accounts")
    r = gql(CREAR_CUENTA, {"n": "Sin token"})
    caso("C1", None, "createAccount", error(r) and contar("accounts") == antes,
         f"{error(r)}; cuentas sin cambio: {contar('accounts') == antes}",
         "Sin encabezado Authorization la ruta no sabe quien llama y no guarda")

    r = gql(CREAR_MOV, mov, t["Maria"])
    caso("C2", t["Maria"], "createTransaction", not error(r) and r["data"]["createTransaction"]["capturedBy"] == m["Maria"],
         r.get("data") or error(r), "El token dice quien es; su rol CAPTURISTA tiene transactions.write")

    antes = contar("accounts")
    r = gql(CREAR_CUENTA, {"n": "Cuenta de Maria"}, t["Maria"])
    caso("C3", t["Maria"], "createAccount", error(r) and contar("accounts") == antes,
         f"{error(r)}; cuentas sin cambio: {contar('accounts') == antes}",
         "Un token valido no abre todas las rutas: CAPTURISTA no tiene accounts.write")

    r = gql(CREAR_CUENTA, {"n": "Banco Luis"}, t["Luis"])
    caso("C4", t["Luis"], "createAccount", not error(r) and r["data"]["createAccount"]["companyId"] == empresa,
         r.get("data") or error(r), "La misma ruta que rechazo a Maria acepta a Luis porque CONTADOR tiene accounts.write")

    antes = contar("transactions")
    r = gql(CREAR_MOV, mov, t["Pedro"])
    caso("C5", t["Pedro"], "createTransaction", error(r) and contar("transactions") == antes,
         f"{error(r)}; movimientos sin cambio: {contar('transactions') == antes}", "CONSULTA no tiene transactions.write")

    r = gql(f'mutation {{ assignRole(input: {{companyUserId: "{m["Pedro"]}", roleId: "{roles["CAPTURISTA"]}"}}) {{ role {{ code }} isActive }} }}', token=t_ana)
    caso("C6", t_ana, "assignRole", not error(r), r.get("data") or error(r),
         "Solo quien tiene roles.write cambia puestos; queda un solo rol activo")

    r = gql(CREAR_MOV, mov, t["Pedro"])
    caso("C7", t["Pedro"], "createTransaction", not error(r), r.get("data") or error(r),
         "El rol no viaja en el token: se lee otra vez en MySQL en cada peticion")

    cuentas_rosa = dato("{ accounts { name } }", "accounts", t_rosa)
    antes = contar("transactions")
    r = gql(CREAR_MOV, mov, t_rosa)
    caso("C8", t_rosa, "accounts / createTransaction", cuentas_rosa == [] and error(r) and contar("transactions") == antes,
         f"accounts con el token de Rosa: {cuentas_rosa}; usar la cuenta {cuenta}: {error(r)}",
         "El token vale para una sola empresa; no lee ni usa las cuentas de otra")

    antes = contar("accounts")
    r1 = gql(CREAR_CUENTA, {"n": "Alterada"}, alterar(t["Luis"]))
    r2 = gql(CREAR_CUENTA, {"n": "Vencida"}, token_vencido(int(m["Luis"]), int(empresa)))
    caso("C9", t["Luis"], "createAccount", error(r1) and error(r2) and contar("accounts") == antes,
         f"alterado: {error(r1)}; vencido: {error(r2)}; cuentas sin cambio: {contar('accounts') == antes}",
         "jwt.decode rechaza firma alterada y exp pasado; no se escribe")

    r = gql('mutation { createAccount(input: {name: "Cuenta suplantada", actorCompanyUserId: "1"}) { id } }', token=t["Maria"])
    caso("C10", t["Maria"], "createAccount con actorCompanyUserId", error(r), error(r),
         "El argumento ya no existe; el id escrito por el cliente no cambia quien llama")

    with open(SALIDA, "w") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    if all(x["ok"] for x in resultados):
        print("\nTodo salio como se esperaba")


if __name__ == "__main__":
    main()
