"""Actividad 5: corre E01-E10 con las operaciones de actividad5/operaciones.graphql
y las variables de actividad5/variables/. Supone la base preparada por pruebas/actividad4.py
(Ana = 1, CAPTURISTA = 3, permisos 1-10). E07 se corre aparte con unittest.

    python pruebas/actividad5.py
"""
import json
import os
import subprocess
import urllib.request

URL = os.getenv("GRAPHQL_URL", "http://localhost:8000/graphql")
MYSQL = os.getenv("MYSQL_CMD", "mysql -h127.0.0.1 -P3307 -uingresos -pingresos ingresos")
BASE = os.path.join(os.path.dirname(__file__), "..", "actividad5")
DOC = open(os.path.join(BASE, "operaciones.graphql")).read()
DOC_ERROR = open(os.path.join(BASE, "operaciones_error.graphql")).read()
SALIDA = os.path.join(os.path.dirname(__file__), "resultados_actividad5.json")

resultados = []

SQL_CAPTURISTA = """SELECT rp.id, p.code, rp.is_active FROM role_permissions rp
JOIN permissions p ON p.id = rp.permission_id WHERE rp.role_id = 3 ORDER BY p.code"""
SQL_REPETIDAS = """SELECT role_id, permission_id, COUNT(*) FROM role_permissions
GROUP BY role_id, permission_id HAVING COUNT(*) > 1"""


def op(nombre, archivo, doc=DOC):
    variables = json.load(open(os.path.join(BASE, "variables", archivo + ".json")))
    body = json.dumps({"query": doc, "operationName": nombre, "variables": variables}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def sql(consulta):
    out = subprocess.run(MYSQL.split() + ["-N", "-e", consulta], capture_output=True, text=True)
    return out.stdout.strip()


def caso(clave, ok, obtenido):
    resultados.append({"caso": clave, "ok": bool(ok), "obtenido": obtenido})
    print("OK   " if ok else "FALLA", clave, "-", obtenido)


def codigos(lista):
    return [p["code"] for p in lista]


def error(r):
    return r["errors"][0]["message"] if r.get("errors") else None


def main():
    # Pedro termino la actividad 4 como CAPTURISTA; no afecta la matriz de roles
    r = op("PuntoDePartida", "e01_punto_de_partida")["data"]
    activos = sorted(x["permission"]["code"] for x in r["rolePermissions"])
    caso("E01", len(r["roles"]) == 4 and len(r["permissions"]) == 10 and activos == json.load(
        open(os.path.join(BASE, "configuracion_inicial.json")))["CAPTURISTA"],
        f"{len(r['roles'])} roles, {len(r['permissions'])} permisos, CAPTURISTA={activos}")

    r = op("ExplorarCatalogo", "e02_explorar_catalogo")["data"]
    todo = op("CatalogoCompleto", "e02_catalogo_completo")["data"]["permissionCatalog"]
    pay = op("CatalogoRecursoInexistente", "e02_catalogo_payments", DOC_ERROR)
    caso("E02", len(r["cuentas"]) == 2 and len(r["movimientos"]) == 2 and len(todo) == 10 and error(pay),
         f"cuentas={len(r['cuentas'])}, movimientos={len(r['movimientos'])}, sin filtro={len(todo)}; PAYMENTS: {error(pay)}")

    antes = sql(SQL_CAPTURISTA)
    p = op("RevisarConfiguracion", "e03_revisar_s1")["data"]["previewRolePermissions"]
    caso("E03", codigos(p["toActivate"]) == ["accounts.write"] and not p["toDeactivate"]
         and len(p["unchanged"]) == 4 and p["finalCount"] == 5 and sql(SQL_CAPTURISTA) == antes,
         f"toActivate={codigos(p['toActivate'])}, toDeactivate={len(p['toDeactivate'])}, "
         f"unchanged={len(p['unchanged'])}, finalCount={p['finalCount']}; SQL igual: {sql(SQL_CAPTURISTA) == antes}")

    a1 = op("AplicarConfiguracion", "e04_aplicar_s1")["data"]["setRolePermissions"]
    despues1 = sql(SQL_CAPTURISTA)
    a2 = op("AplicarConfiguracion", "e04_aplicar_s1")["data"]["setRolePermissions"]
    caso("E04", a1["changed"] and not a2["changed"] and not a2["activated"] and not a2["deactivated"]
         and a2["finalCount"] == 5 and sql(SQL_CAPTURISTA) == despues1 and sql(SQL_REPETIDAS) == "",
         f"1a changed={a1['changed']}, 2a changed={a2['changed']}, finalCount={a2['finalCount']}, sin duplicados")

    def id_aw():
        return [l for l in sql(SQL_CAPTURISTA).splitlines() if "accounts.write" in l][0]
    m1 = id_aw()
    op("AplicarConfiguracion", "e05_aplicar_s0")
    m2 = id_aw()
    op("AplicarConfiguracion", "e05_aplicar_s1")
    m3 = id_aw()
    mismo = m1.split()[0] == m2.split()[0] == m3.split()[0]
    caso("E05", mismo and m2.endswith("0") and m3.endswith("1"), f"{m1!r} -> {m2!r} -> {m3!r}")

    antes = sql(SQL_CAPTURISTA)
    variantes = [
        ("e06_rol_inexistente", None, None),
        ("e06_rol_inactivo", "UPDATE roles SET is_active = 0 WHERE code = 'CONSULTA'",
         "UPDATE roles SET is_active = 1 WHERE code = 'CONSULTA'"),
        ("e06_administrador", None, None),
        ("e06_permiso_inexistente", None, None),
        ("e06_permiso_inactivo", "UPDATE permissions SET is_active = 0 WHERE code = 'concepts.write'",
         "UPDATE permissions SET is_active = 1 WHERE code = 'concepts.write'"),
        ("e06_repetido", None, None),
    ]
    tabla = {}
    for archivo, prep, rest in variantes:
        if prep:
            sql(prep)
        e1 = error(op("RevisarConfiguracion", archivo))
        e2 = error(op("AplicarConfiguracion", archivo))
        if rest:
            sql(rest)
        tabla[archivo] = [e1, e2]
    caso("E06", all(a and b for a, b in tabla.values()) and sql(SQL_CAPTURISTA) == antes, tabla)

    v = op("AplicarConfiguracion", "e08_lista_vacia")["data"]["setRolePermissions"]
    activos = [l for l in sql(SQL_CAPTURISTA).splitlines() if l.endswith("1")]
    caso("E08", v["finalCount"] == 0 and not activos,
         f"deactivated={codigos(v['deactivated'])}; reiniciar la API y volver a revisar (ver README)")

    op("AplicarConfiguracion", "e09_restaurar_s0")
    final = {}
    for linea in sql("""SELECT r.code, p.code FROM role_permissions rp JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id WHERE rp.is_active = 1 ORDER BY r.code, p.code""").splitlines():
        rol, perm = linea.split()
        final.setdefault(rol, []).append(perm)
    with open(os.path.join(BASE, "configuracion_final.json"), "w") as f:
        f.write(json.dumps(final, indent=2) + "\n")
    caso("E09", final == json.load(open(os.path.join(BASE, "configuracion_inicial.json"))),
         "configuracion_final.json igual a configuracion_inicial.json")

    cuentas = op("ConsultarCuentas", "e10_consultar_cuentas")
    mov = op("RegistrarMovimiento", "e10_registrar_movimiento")
    caso("E10", not cuentas.get("errors") and not mov.get("errors"),
         mov.get("data") or error(mov))

    with open(SALIDA, "w") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
