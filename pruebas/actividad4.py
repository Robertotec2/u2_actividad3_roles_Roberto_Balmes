import json
import os
import subprocess
import sys
import urllib.request

URL = os.getenv("GRAPHQL_URL", "http://localhost:8000/graphql")
SALIDA = os.path.join(os.path.dirname(__file__), "resultados.json")
MYSQL = os.getenv("MYSQL_CMD", "mysql -h127.0.0.1 -P3307 -uingresos -pingresos ingresos")

pasos = []
hooks = {"graphql": None, "sql": None}


def gql(query):
    req = urllib.request.Request(
        URL, data=json.dumps({"query": query}).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def sql(consulta):
    out = subprocess.run(MYSQL.split() + ["-t", "-e", consulta], capture_output=True, text=True)
    return out.stdout.strip()


def paso(clave, titulo, regla, query, espera_error=False):
    resp = hooks["graphql"](clave, query) if hooks["graphql"] else gql(query)
    ok = bool(resp.get("errors")) == espera_error
    pasos.append({"clave": clave, "titulo": titulo, "regla": regla, "tipo": "graphql",
                  "query": query.strip(), "respuesta": resp, "ok": ok})
    print(("OK   " if ok else "FALLA"), clave, "-", titulo)
    return resp.get("data")


def paso_sql(clave, titulo, regla, consulta):
    salida = sql(consulta)
    if hooks["sql"]:
        hooks["sql"](clave, consulta, salida)
    pasos.append({"clave": clave, "titulo": titulo, "regla": regla, "tipo": "sql",
                  "query": consulta.strip(), "respuesta": salida, "ok": True})
    print("SQL  ", clave, "-", titulo)


def dato(query, campo):
    r = gql(query)
    if r.get("errors"):
        raise SystemExit(f"Error preparando datos: {r['errors'][0]['message']}")
    return r["data"][campo]


SELECT_LISTA = """SELECT r.code AS rol, p.code AS permiso, rp.is_active
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
ORDER BY r.code, p.code;"""


def main():
    n = sys.argv[1] if len(sys.argv) > 1 else "4"

    empresa = dato(f'mutation {{ createCompany(input: {{name: "Comercial del Sureste", rfc: "CSU2610{n:0>2}AA1"}}) {{ id }} }}', "createCompany")["id"]
    otra = dato(f'mutation {{ createCompany(input: {{name: "Abarrotes Kanasin", rfc: "AKA2610{n:0>2}BB2"}}) {{ id }} }}', "createCompany")["id"]
    ana = dato(f'mutation {{ createCompanyAdmin(input: {{companyId: "{empresa}", name: "Ana", email: "ana{n}@sureste.mx", password: "ana123"}}) {{ id }} }}', "createCompanyAdmin")["id"]
    rosa = dato(f'mutation {{ createCompanyAdmin(input: {{companyId: "{otra}", name: "Rosa", email: "rosa{n}@kanasin.mx", password: "rosa123"}}) {{ id }} }}', "createCompanyAdmin")["id"]

    roles = {r["code"]: r["id"] for r in dato("{ roles { id code } }", "roles")}
    perms = {p["code"]: p["id"] for p in dato("{ permissions { id code } }", "permissions")}

    m = {}
    for nombre, rol in [("Luis", "CONTADOR"), ("Maria", "CAPTURISTA"), ("Jose", "CAPTURISTA"), ("Pedro", "CONSULTA")]:
        m[nombre] = dato(f'mutation {{ createCompanyUser(input: {{actorCompanyUserId: "{ana}", name: "{nombre}", email: "{nombre.lower()}{n}@sureste.mx", password: "{nombre.lower()}123"}}) {{ id }} }}', "createCompanyUser")["id"]
        dato(f'mutation {{ assignRole(input: {{actorCompanyUserId: "{ana}", companyUserId: "{m[nombre]}", roleId: "{roles[rol]}"}}) {{ id }} }}', "assignRole")

    cuenta = dato(f'mutation {{ createAccount(input: {{actorCompanyUserId: "{m["Luis"]}", name: "Caja general"}}) {{ id }} }}', "createAccount")["id"]
    concepto = dato(f'mutation {{ createConcept(input: {{actorCompanyUserId: "{m["Luis"]}", name: "Venta de mostrador", type: INCOME}}) {{ id }} }}', "createConcept")["id"]
    dato(f'mutation {{ assignConceptToAccount(input: {{actorCompanyUserId: "{m["Luis"]}", accountId: "{cuenta}", conceptId: "{concepto}"}}) {{ id }} }}', "assignConceptToAccount")

    paso("P0", "Las cinco personas de la empresa con su rol",
         "Cada persona tiene un lugar en la empresa y un solo puesto; Ana es la administradora principal",
         f"""query {{
  companyUsers(actorCompanyUserId: "{ana}") {{
    id
    isAdmin
    user {{ name }}
    role {{ code }}
  }}
}}""")

    paso("P1.1", "roles muestra los cuatro puestos",
         "El catálogo trae exactamente los cuatro roles de la tabla",
         """query {
  roles {
    id
    code
    name
  }
}""")
    paso("P1.2", "permissions muestra los diez códigos",
         "El catálogo trae los diez permisos; no hay uno por persona",
         """query {
  permissions {
    id
    code
  }
}""")

    def lista(rol):
        return f"""query {{
  rolePermissions(roleId: "{roles[rol]}") {{
    role {{ code }}
    permission {{ code }}
    isActive
  }}
}}"""

    paso("P1.3", "Lista del capturista antes del cambio",
         "CAPTURISTA tiene transactions.write pero no accounts.write", lista("CAPTURISTA"))
    paso("P1.4", "Lista de consulta",
         "CONSULTA no tiene ningún permiso .write, solo ve", lista("CONSULTA"))
    paso("P1.5", "Lista del contador (antes del cambio de Pedro)",
         "CONTADOR tiene accounts.write y no tiene roles.write", lista("CONTADOR"))
    paso("P1.6", "Lista del administrador",
         "ADMINISTRADOR tiene los diez permisos", lista("ADMINISTRADOR"))

    def crear_cuenta(actor, nombre):
        return f"""mutation {{
  createAccount(
    input: {{ actorCompanyUserId: "{actor}", name: "{nombre}" }}
  ) {{
    id
    companyId
    name
  }}
}}"""

    cuentas_sql = f"SELECT id, company_id, name FROM accounts WHERE company_id = {empresa};"
    paso_sql("P2.0", "Cuentas en MySQL antes de la Parte 2",
             "Punto de partida para ver que un rechazo no guarda filas", cuentas_sql)
    paso("P2.1", "María intenta createAccount",
         "El rol CAPTURISTA no tiene accounts.write: exigir_permiso rechaza antes del commit",
         crear_cuenta(m["Maria"], "Cuenta de Maria"), espera_error=True)
    paso("P2.2", "José intenta createAccount",
         "José tiene el mismo rol que María y recibe el mismo rechazo",
         crear_cuenta(m["Jose"], "Cuenta de Jose"), espera_error=True)
    paso_sql("P2.2b", "Las cuentas no cambiaron tras los rechazos",
             "Un rechazo no guarda la fila: no hubo commit", cuentas_sql)

    def asignar(actor, rol, perm):
        return f"""mutation {{
  assignPermissionToRole(
    input: {{
      actorCompanyUserId: "{actor}"
      roleId: "{roles[rol]}"
      permissionId: "{perms[perm]}"
    }}
  ) {{
    role {{ code }}
    permission {{ code }}
    isActive
  }}
}}"""

    def quitar(actor, rol, perm):
        return f"""mutation {{
  removePermissionFromRole(
    actorCompanyUserId: "{actor}"
    roleId: "{roles[rol]}"
    permissionId: "{perms[perm]}"
  )
}}"""

    paso("P2.3", "Ana agrega accounts.write al rol CAPTURISTA",
         "El cambio se hace una sola vez, en el rol, por alguien con roles.write",
         asignar(ana, "CAPTURISTA", "accounts.write"))
    paso("P2.3b", "Lista del capturista después del cambio",
         "La lista del rol ya incluye accounts.write", lista("CAPTURISTA"))
    paso("P2.4", "María crea una cuenta después del cambio",
         "María recibe el permiso nuevo por su rol", crear_cuenta(m["Maria"], "Cuenta de Maria"))
    paso("P2.5", "José crea una cuenta después del cambio",
         "José también puede y no se editó su ficha: el permiso vive en el rol",
         crear_cuenta(m["Jose"], "Cuenta de Jose"))
    paso("P2.6", "Ana quita accounts.write del rol CAPTURISTA",
         "removePermissionFromRole desactiva la pareja", quitar(ana, "CAPTURISTA", "accounts.write"))
    paso_sql("P2.6b", "La pareja CAPTURISTA / accounts.write queda inactiva en MySQL",
             "La fila sigue en role_permissions con is_active = 0, no se borró",
             """SELECT rp.id, r.code AS rol, p.code AS permiso, rp.is_active
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
WHERE r.code = 'CAPTURISTA'
ORDER BY p.code;""")
    paso("P2.7a", "María vuelve a recibir rechazo",
         "Al quitar el permiso del rol María deja de poder",
         crear_cuenta(m["Maria"], "Otra cuenta de Maria"), espera_error=True)
    paso("P2.7b", "José vuelve a recibir rechazo",
         "José también queda fuera con el mismo cambio en el rol",
         crear_cuenta(m["Jose"], "Otra cuenta de Jose"), espera_error=True)

    def mov(actor):
        return f"""mutation {{
  createTransaction(
    input: {{
      actorCompanyUserId: "{actor}"
      accountId: "{cuenta}"
      conceptId: "{concepto}"
      amount: "350.00"
      description: "Venta de Pedro"
    }}
  ) {{
    id
    type
    amount
    capturedBy
  }}
}}"""

    conteo = f"SELECT COUNT(*) AS movimientos FROM transactions WHERE company_id = {empresa};"
    roles_pedro = f"""SELECT cur.id, r.code AS rol, cur.is_active
FROM company_user_roles cur
JOIN roles r ON r.id = cur.role_id
WHERE cur.company_user_id = {m["Pedro"]};"""

    paso_sql("P3.0", "Movimientos antes del intento de Pedro", "Conteo de referencia", conteo)
    paso("P3.1", "Pedro (consulta) intenta createTransaction",
         "CONSULTA no tiene transactions.write: se rechaza", mov(m["Pedro"]), espera_error=True)
    paso_sql("P3.1b", "Movimientos después del rechazo",
             "La tabla de movimientos no ganó la fila", conteo)
    paso("P3.2", "Ana usa assignRole para dejar a Pedro como CAPTURISTA",
         "assignRole desactiva el rol anterior y deja uno solo activo",
         f"""mutation {{
  assignRole(
    input: {{
      actorCompanyUserId: "{ana}"
      companyUserId: "{m["Pedro"]}"
      roleId: "{roles["CAPTURISTA"]}"
    }}
  ) {{
    companyUser {{
      user {{ name }}
      role {{ code }}
    }}
    role {{ code }}
    isActive
  }}
}}""")
    paso("P3.3", "Pedro registra el movimiento ya como capturista",
         "Su lista nueva es la del puesto nuevo", mov(m["Pedro"]))
    paso("P3.4", "Lista del contador después del cambio de Pedro",
         "Cambiar el puesto de Pedro no tocó la lista del contador", lista("CONTADOR"))
    paso("P3.4b", "Luis sigue pudiendo crear una cuenta",
         "Luis conserva accounts.write porque su rol no cambió", crear_cuenta(m["Luis"], "Bancos"))
    paso("P3.5", "Lista de consulta después del cambio de Pedro",
         "CONSULTA sigue sin permisos .write; Pedro ya no la usa pero la lista no cambió",
         lista("CONSULTA"))
    paso_sql("P3.6", "Roles de Pedro en company_user_roles",
             "Pedro tiene un solo rol activo; el anterior queda inactivo, no se borra", roles_pedro)

    activos_consulta = """SELECT r.code AS rol, p.code AS permiso, rp.is_active
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
WHERE r.code = 'CONSULTA' AND rp.is_active = 1
ORDER BY p.code;"""
    paso("P4.1", "José intenta agregar concepts.write al rol CONSULTA",
         "Cambiar la lista pide roles.write y el capturista no lo tiene",
         asignar(m["Jose"], "CONSULTA", "concepts.write"), espera_error=True)
    paso_sql("P4.2", "La lista activa de CONSULTA en MySQL no cambió",
             "El rechazo no dejó ninguna fila nueva", activos_consulta)
    paso("P4.3", "Ana hace la misma operación",
         "El administrador sí tiene roles.write", asignar(ana, "CONSULTA", "concepts.write"))
    paso("P4.4", "Ana quita concepts.write de CONSULTA",
         "Consulta vuelve a quedar sin permisos de escritura", quitar(ana, "CONSULTA", "concepts.write"))
    paso_sql("P4.4b", "Lista activa de CONSULTA al final",
             "Solo quedan los cuatro permisos .read", activos_consulta)

    paso("PX.1", "Rosa (admin de otra empresa) crea una cuenta",
         "La cuenta se guarda en la empresa de Rosa, la empresa sale de su membresía y no del cliente",
         crear_cuenta(rosa, "Caja Kanasin"))
    paso("PX.2", "Ana consulta las cuentas",
         "Ana solo ve las cuentas de su empresa; la de Rosa no aparece",
         f"""query {{
  accounts(actorCompanyUserId: "{ana}") {{
    id
    companyId
    name
  }}
}}""")

    paso_sql("PF.1", "SELECT final de role_permissions",
             "La lista de los cuatro roles coincide con la tabla del documento", SELECT_LISTA)
    paso_sql("PF.2", "Permisos activos por rol",
             "ADMINISTRADOR 10, CONTADOR 8, CAPTURISTA 4, CONSULTA 4",
             """SELECT r.code AS rol, SUM(rp.is_active) AS activos, COUNT(*) AS filas
FROM role_permissions rp JOIN roles r ON r.id = rp.role_id
GROUP BY r.id, r.code ORDER BY r.id;""")

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump({"ids": {"empresa": empresa, "otra": otra, "ana": ana, "rosa": rosa,
                           **{k.lower(): v for k, v in m.items()}, "roles": roles},
                   "pasos": pasos}, f, ensure_ascii=False, indent=2)
    fallas = [p["clave"] for p in pasos if not p["ok"]]
    print("\nTodo salió como se esperaba" if not fallas else f"\nFallaron: {fallas}")


if __name__ == "__main__":
    main()
