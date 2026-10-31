"""Actividad 7: corre los casos B01 a B15 y escribe actividad7/evidencias.md y pruebas/resultados_actividad7.json.

Cada caso adicional usa su propia empresa (pruebas/actividad7_datos.py), asi el conjunto de
referencia no se altera. B07, B08 y B14 preparan el estado con SQL / setRolePermissions y lo restauran.

    python pruebas/actividad7.py
"""
import json
import os
from datetime import datetime, timezone

from jwt_lab import gql, dato, error, sql, login, alterar, token_vencido
from actividad7_datos import preparar_referencia, nueva_empresa, crear_cuenta, crear_concepto, permitir, mover

RAIZ = os.path.join(os.path.dirname(__file__), "..")
CAMPOS = "accountId accountName isActive openingBalance totalIncome totalExpense profit closingBalance isInRed"
CUENTA = f"""query($id: ID!, $from: Date!, $to: Date!) {{
  accountBalance(accountId: $id, fromDate: $from, toDate: $to) {{ {CAMPOS} }}
}}"""
GENERAL = f"""query($from: Date!, $to: Date!) {{
  generalBalance(fromDate: $from, toDate: $to) {{
    companyId currency openingBalance totalIncome totalExpense profit closingBalance isInRed accountsInRed
    accounts {{ {CAMPOS} }}
  }}
}}"""
PERIODO = {"from": "2026-10-26", "to": "2026-10-30"}

resultados = []


def cuenta(token, cid, desde="2026-10-26", hasta="2026-10-30"):
    return gql(CUENTA, {"id": cid, "from": desde, "to": hasta}, token)


def general(token, desde="2026-10-26", hasta="2026-10-30"):
    return gql(GENERAL, {"from": desde, "to": hasta}, token)


def resumen(b):
    return (f"inicial {b['openingBalance']}, ingresos {b['totalIncome']}, egresos {b['totalExpense']}, "
            f"profit {b['profit']}, final {b['closingBalance']}, enRojo {str(b['isInRed']).lower()}")


def caso(clave, prueba, ok, obtenido, regla):
    resultados.append({"caso": clave, "prueba": prueba, "ok": bool(ok), "obtenido": obtenido, "regla": regla})
    print("OK   " if ok else "FALLA", clave, "-", obtenido)


def contar_movimientos(empresa):
    return sql(f"SELECT COUNT(*) FROM transactions WHERE company_id = {int(empresa)}")


def main():
    ref = preparar_referencia()
    t, cs = ref["token"], ref["cuentas"]

    # B01
    huella = "SELECT id, account_id, type, amount, transaction_date, is_active FROM transactions WHERE company_id = %d ORDER BY id" % int(ref["empresa"])
    antes = sql(huella)
    bs = {n: cuenta(t, cs[n])["data"]["accountBalance"] for n in ("Banco", "Caja", "Ahorro")}
    g = general(t)["data"]["generalBalance"]
    esperado = {"Banco": ("1000.00", "3000.00", "2200.00", "800.00", "1800.00", False),
                "Caja": ("0.00", "500.00", "700.00", "-200.00", "-200.00", True),
                "Ahorro": ("0.00", "0.00", "0.00", "0.00", "0.00", False)}
    cif = lambda b: (b["openingBalance"], b["totalIncome"], b["totalExpense"], b["profit"], b["closingBalance"], b["isInRed"])
    ok = all(cif(bs[n]) == esperado[n] for n in bs) and cif(g) == ("1000.00", "3500.00", "2900.00", "600.00", "1600.00", False) \
        and g["accountsInRed"] == 1 and sql(huella) == antes
    caso("B01", "Consultar Banco, Caja, Ahorro y el general del 26 al 30", ok,
         "; ".join(f"{n}: {resumen(b)}" for n, b in bs.items()) +
         f"; General: {resumen(g)}, accountsInRed {g['accountsInRed']}; filas de transactions iguales antes y despues: {sql(huella) == antes}",
         "El saldo inicial sale de los movimientos anteriores al periodo y consultar no guarda ni modifica filas")

    # B02
    b = cuenta(t, cs["Banco"], "2026-10-28", "2026-10-28")["data"]["accountBalance"]
    caso("B02", "Consultar Banco unicamente el 28", cif(b) == ("2800.00", "0.00", "1000.00", "-1000.00", "1800.00", False),
         f"Banco 28: {resumen(b)}", "Un profit negativo del dia no implica saldo final negativo")

    # B03
    vacia = nueva_empresa("Empresa sin cuentas")
    g3 = general(vacia["token"])["data"]["generalBalance"]
    caso("B03", "Consultar una empresa sin cuentas",
         g3["accounts"] == [] and cif(g3) == ("0.00",) * 5 + (False,) and g3["accountsInRed"] == 0,
         f"accounts [], {resumen(g3)}, accountsInRed {g3['accountsInRed']}",
         "Sin cuentas el general devuelve ceros, no null")

    # B04
    e = nueva_empresa()
    c = crear_cuenta(e["token"], "Limites")
    k = crear_concepto(e["token"], "Deposito", "INCOME")
    permitir(e["token"], c, k)
    for monto, fecha in [("1.00", "2026-10-25T23:59:59Z"), ("10.00", "2026-10-26T00:00:00Z"),
                         ("100.00", "2026-10-30T23:59:59Z"), ("1000.00", "2026-10-31T00:00:00Z")]:
        mover(e["token"], c, k, monto, fecha)
    b = cuenta(e["token"], c)["data"]["accountBalance"]
    caso("B04", "Movimientos 25 23:59:59, 26 00:00:00, 30 23:59:59 y 31 00:00:00 (1, 10, 100 y 1000)",
         (b["openingBalance"], b["totalIncome"], b["closingBalance"]) == ("1.00", "110.00", "111.00"),
         resumen(b), "Inicio incluido y fin excluido: [26 00:00Z, 31 00:00Z); el del 31 queda fuera")

    # B05
    e = preparar_referencia()
    m = mover(e["token"], e["cuentas"]["Banco"], e["conceptos"]["Renta"], "100.00", "2026-10-27T12:00:00Z", "Gasto capturado tarde")
    b = cuenta(e["token"], e["cuentas"]["Banco"])["data"]["accountBalance"]
    b27 = cuenta(e["token"], e["cuentas"]["Banco"], "2026-10-27", "2026-10-27")["data"]["accountBalance"]
    caso("B05", "Capturar un egreso del 27 con capturedAt posterior",
         m["capturedAt"] > m["transactionDate"] and b["totalExpense"] == "2300.00" and b27["totalExpense"] == "1300.00",
         f"transactionDate {m['transactionDate']}, capturedAt {m['capturedAt']}; Banco 26-30 egresos {b['totalExpense']}, "
         f"final {b['closingBalance']}; Banco solo 27 egresos {b27['totalExpense']}",
         "El movimiento cuenta en el dia de transactionDate, no en el de captura")

    # B06
    e = nueva_empresa()
    c = crear_cuenta(e["token"], "Centavos")
    i, s = crear_concepto(e["token"], "Entrada", "INCOME"), crear_concepto(e["token"], "Salida", "EXPENSE")
    permitir(e["token"], c, i)
    permitir(e["token"], c, s)
    for k, monto in [(i, "0.10"), (i, "0.20"), (s, "0.30")]:
        mover(e["token"], c, k, monto, "2026-10-27T12:00:00Z")
    b = cuenta(e["token"], c)["data"]["accountBalance"]
    caso("B06", "Ingresos 0.10 y 0.20 y egreso 0.30 en una cuenta vacia",
         (b["profit"], b["closingBalance"], b["isInRed"]) == ("0.00", "0.00", False), resumen(b),
         "Decimal sin float: 0.10 + 0.20 - 0.30 da exactamente 0.00")

    # B07
    e = preparar_referencia()
    mid = [x for x in e["movimientos"] if x["descripcion"] == "Compra de materiales"][0]["id"]
    sql(f"UPDATE transactions SET is_active = 0 WHERE id = {int(mid)}")
    b = cuenta(e["token"], e["cuentas"]["Banco"])["data"]["accountBalance"]
    g7 = general(e["token"])["data"]["generalBalance"]
    sql(f"UPDATE transactions SET is_active = 1 WHERE id = {int(mid)}")
    b_rest = cuenta(e["token"], e["cuentas"]["Banco"])["data"]["accountBalance"]
    caso("B07", f"Desactivar el movimiento {mid} (Compra de materiales 1000.00) y volver a consultar",
         b["totalExpense"] == "1200.00" and b["closingBalance"] == "2800.00" and g7["closingBalance"] == "2600.00"
         and b_rest["closingBalance"] == "1800.00",
         f"Banco con el movimiento inactivo: {resumen(b)}; general final {g7['closingBalance']}; "
         f"al reactivarlo Banco vuelve a {b_rest['closingBalance']}",
         "Un movimiento inactivo no participa; los demas se conservan")

    # B08
    e = preparar_referencia()
    sql(f"UPDATE accounts SET is_active = 0 WHERE id = {int(e['cuentas']['Caja'])}")
    g8 = general(e["token"])["data"]["generalBalance"]
    caja = [a for a in g8["accounts"] if a["accountName"] == "Caja"][0]
    sql(f"UPDATE accounts SET is_active = 1 WHERE id = {int(e['cuentas']['Caja'])}")
    caso("B08", "Desactivar Caja, que tiene movimientos validos",
         caja["isActive"] is False and caja["closingBalance"] == "-200.00" and g8["closingBalance"] == "1600.00",
         f"Caja: isActive {str(caja['isActive']).lower()}, final {caja['closingBalance']}; general final {g8['closingBalance']}, accountsInRed {g8['accountsInRed']}",
         "Desactivar una cuenta no borra su historial; sigue sumando al general")

    # B09
    e = preparar_referencia()
    antes9 = general(e["token"])["data"]["generalBalance"]
    extra = crear_concepto(e["token"], "Comisiones", "INCOME")
    permitir(e["token"], e["cuentas"]["Banco"], extra)
    permitir(e["token"], e["cuentas"]["Banco"], e["conceptos"]["Ventas"])
    despues9 = general(e["token"])["data"]["generalBalance"]
    caso("B09", "Agregar dos conceptos mas a Banco sin movimientos nuevos", antes9 == despues9,
         f"General antes: {resumen(antes9)}; despues: {resumen(despues9)}",
         "El calculo no se une a account_concepts, asi que no se duplican importes")

    # B10
    r1 = cuenta(t, cs["Banco"], "2026-10-30", "2026-10-26")
    r2 = general(t, "2026-10-30", "2026-10-26")
    r3 = general(t, "2026-02-30", "2026-03-01")
    caso("B10", "fromDate posterior a toDate y fecha inexistente 2026-02-30",
         all(error(r) and not r.get("data") for r in (r1, r2, r3)),
         f"accountBalance: {error(r1)}; generalBalance: {error(r2)}; 2026-02-30: {error(r3)}",
         "Las fechas se validan antes de calcular; no se devuelve un balance")

    # B11
    payload = json.loads(__import__("base64").urlsafe_b64decode(t.split(".")[1] + "=="))
    vencido = token_vencido(payload["companyUserId"], payload["companyId"])
    msgs = []
    for nombre, tok in [("sin token", None), ("alterado", alterar(t)), ("vencido", vencido)]:
        a = cuenta(tok, cs["Banco"])
        gg = general(tok)
        msgs.append((nombre, error(a), error(gg), a.get("data"), gg.get("data")))
    caso("B11", "Consultar sin token, con token alterado y con token vencido",
         all(x[1] and x[2] and not x[3] and not x[4] for x in msgs),
         "; ".join(f"{n}: {ea} / {eg}" for n, ea, eg, _, _ in msgs),
         "Las dos consultas validan el token antes de devolver informacion")

    # B12
    otra = preparar_referencia()
    r = cuenta(t, otra["cuentas"]["Banco"])
    inexistente = cuenta(t, "999999")
    g12 = general(t)["data"]["generalBalance"]
    solo_a = sorted(x["accountId"] for x in g12["accounts"]) == sorted(cs.values())
    caso("B12", "Token de la empresa A con el id de Banco de la empresa B; despues el general de A",
         error(r) == "Cuenta no disponible" == error(inexistente) and r["data"] is None and solo_a,
         f"cuenta de B: {error(r)} (data null); cuenta inexistente: {error(inexistente)}; general de A solo trae sus cuentas: {solo_a}",
         "Una cuenta ajena y una inexistente responden igual y no se revelan datos de otra empresa")

    # B13
    roles = {x["code"]: x["id"] for x in dato("{ roles { id code } }", "roles")}
    email = f"consulta.{ref['sufijo'].lower()}@balances.test"
    cu = dato(f'mutation {{ createCompanyUser(input: {{name: "Consulta", email: "{email}", password: "lab123"}}) {{ id }} }}', "createCompanyUser", t)["id"]
    dato(f'mutation {{ assignRole(input: {{companyUserId: "{cu}", roleId: "{roles["CONSULTA"]}"}}) {{ id }} }}', "assignRole", t)
    tc = login(email, "lab123")
    lee = cuenta(tc, cs["Banco"])
    lee_g = general(tc)
    n_antes = contar_movimientos(ref["empresa"])
    escribe = gql("""mutation($a: ID!, $c: ID!) { createTransaction(input: {accountId: $a, conceptId: $c, amount: "10.00"}) { id } }""",
                  {"a": cs["Banco"], "c": ref["conceptos"]["Servicios"]}, tc)
    caso("B13", "Rol CONSULTA: leer balances y despues intentar createTransaction",
         not error(lee) and not error(lee_g) and error(escribe) and contar_movimientos(ref["empresa"]) == n_antes,
         f"accountBalance Banco final {lee['data']['accountBalance']['closingBalance']}; general final "
         f"{lee_g['data']['generalBalance']['closingBalance']}; createTransaction: {error(escribe)}; "
         f"movimientos {n_antes} -> {contar_movimientos(ref['empresa'])}",
         "accounts.read y transactions.read bastan para leer; capturar sigue pidiendo transactions.write")

    # B14
    consulta_perms = [p["permission"]["id"] for p in dato(f'{{ rolePermissions(roleId: "{roles["CONSULTA"]}") {{ permission {{ id code }} }} }}', "rolePermissions")
                      if p["permission"]["code"] != "transactions.read"]
    original = [p["permission"]["id"] for p in dato(f'{{ rolePermissions(roleId: "{roles["CONSULTA"]}") {{ permission {{ id }} }} }}', "rolePermissions")]
    aplicar = """mutation($i: SetRolePermissionsInput!) { setRolePermissions(input: $i) { finalCount } }"""
    dato(aplicar, "setRolePermissions", t, {"i": {"roleId": roles["CONSULTA"], "permissionIds": consulta_perms}})
    sin_a = cuenta(tc, cs["Banco"])
    sin_g = general(tc)
    dato(aplicar, "setRolePermissions", t, {"i": {"roleId": roles["CONSULTA"], "permissionIds": original}})
    vuelve = cuenta(tc, cs["Banco"])
    caso("B14", "Quitar transactions.read a CONSULTA conservando accounts.read, con el mismo token",
         error(sin_a) and error(sin_g) and not error(vuelve),
         f"accountBalance: {error(sin_a)}; generalBalance: {error(sin_g)}; permiso restaurado y vuelve a leer: {not error(vuelve)}",
         "El permiso se lee en MySQL en cada peticion; faltando uno de los dos se rechaza")

    # B15
    e = nueva_empresa("Empresa en rojo")
    c = crear_cuenta(e["token"], "Gastos")
    k = crear_concepto(e["token"], "Papeleria", "EXPENSE")
    permitir(e["token"], c, k)
    mover(e["token"], c, k, "50.00", "2026-10-27T12:00:00Z")
    b = cuenta(e["token"], c)["data"]["accountBalance"]
    g15 = general(e["token"])["data"]["generalBalance"]
    caso("B15", "Egreso de 50.00 en una cuenta vacia de una empresa sin otros saldos",
         b["closingBalance"] == "-50.00" and b["isInRed"] and g15["isInRed"] and g15["accountsInRed"] == 1,
         f"Cuenta: {resumen(b)}; general final {g15['closingBalance']}, isInRed {str(g15['isInRed']).lower()}, accountsInRed {g15['accountsInRed']}",
         "Se permite dejar saldo negativo y el backend lo informa; el monto se guarda positivo y EXPENSE resta")

    with open(os.path.join(os.path.dirname(__file__), "resultados_actividad7.json"), "w") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    escribir_evidencias()
    if all(x["ok"] for x in resultados):
        print("\nTodo salio como se esperaba")


def escribir_evidencias():
    hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lineas = [
        "# Evidencias - Actividad 7: balances por cuenta y balance general", "",
        "Integrantes: Roberto Balmes Solis, David Romero", "",
        f"Generado por `python pruebas/actividad7.py` el {hoy}. Cada caso adicional usa su propia empresa de prueba,",
        "asi el conjunto de referencia (Banco, Caja, Ahorro) no se altera. Los resultados completos estan en",
        "`pruebas/resultados_actividad7.json` y las pruebas automatizadas en `tests/test_balances.py`",
        "(salida en `actividad7/salida_tests.txt`).", "",
        "Periodo de referencia: 2026-10-26 al 2026-10-30, dias completos en UTC.", "",
    ]
    for r in resultados:
        lineas += [f"## {r['caso']}. {r['prueba']}", "",
                   f"- **Resultado:** {'correcto' if r['ok'] else 'NO coincide'}",
                   f"- **Obtenido:** {r['obtenido']}",
                   f"- **Regla comprobada:** {r['regla']}", ""]
    with open(os.path.join(RAIZ, "actividad7", "evidencias.md"), "w") as f:
        f.write("\n".join(lineas))


if __name__ == "__main__":
    main()
