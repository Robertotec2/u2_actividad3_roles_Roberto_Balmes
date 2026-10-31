"""Actividad 7: prepara una empresa de prueba con Banco, Caja y Ahorro y los movimientos de referencia.

Cada llamada crea una empresa nueva, asi los casos adicionales no alteran el conjunto de referencia.
Al correrlo directo tambien escribe actividad7/variables/*.json con los ids reales:

    python pruebas/actividad7_datos.py
"""
import json
import os
import uuid

from jwt_lab import dato, login

CREAR_MOV = """mutation($a: ID!, $c: ID!, $m: Decimal!, $f: DateTime, $d: String) {
  createTransaction(input: {accountId: $a, conceptId: $c, amount: $m, transactionDate: $f, description: $d}) {
    id transactionDate capturedAt
  }
}"""

# (cuenta, fecha de operacion, concepto, importe, descripcion) - todos a las 12:00:00Z
MOVIMIENTOS = [
    ("Banco", "2026-10-25T12:00:00Z", "Apertura", "1000.00", "Ingreso de apertura anterior al periodo"),
    ("Banco", "2026-10-26T12:00:00Z", "Servicios", "3000.00", "Cobro de servicios"),
    ("Banco", "2026-10-27T12:00:00Z", "Renta", "1200.00", "Pago de renta"),
    ("Banco", "2026-10-28T12:00:00Z", "Materiales", "1000.00", "Compra de materiales"),
    ("Caja", "2026-10-26T12:00:00Z", "Ventas", "500.00", "Venta de contado"),
    ("Caja", "2026-10-29T12:00:00Z", "Insumos", "700.00", "Pago de insumos"),
]

CONCEPTOS = [("Apertura", "INCOME"), ("Servicios", "INCOME"), ("Ventas", "INCOME"),
             ("Renta", "EXPENSE"), ("Materiales", "EXPENSE"), ("Insumos", "EXPENSE")]

PERMITIDOS = {"Banco": ["Apertura", "Servicios", "Renta", "Materiales"], "Caja": ["Ventas", "Insumos"], "Ahorro": []}


def nueva_empresa(nombre="Balances Lab"):
    suf = uuid.uuid4().hex[:8].upper()
    empresa = dato(f'mutation {{ createCompany(input: {{name: "{nombre}", rfc: "LAB{suf}"}}) {{ id }} }}', "createCompany")["id"]
    email = f"admin.{suf.lower()}@balances.test"
    dato(f'mutation {{ createCompanyAdmin(input: {{companyId: "{empresa}", name: "Admin {suf}", email: "{email}", password: "lab123"}}) {{ id }} }}',
         "createCompanyAdmin")
    return {"empresa": empresa, "token": login(email, "lab123"), "sufijo": suf}


def crear_cuenta(token, nombre):
    return dato('mutation($n: String!) { createAccount(input: {name: $n}) { id } }', "createAccount", token, {"n": nombre})["id"]


def crear_concepto(token, nombre, tipo):
    return dato(f'mutation($n: String!) {{ createConcept(input: {{name: $n, type: {tipo}}}) {{ id }} }}', "createConcept", token, {"n": nombre})["id"]


def permitir(token, cuenta, concepto):
    dato(f'mutation {{ assignConceptToAccount(input: {{accountId: "{cuenta}", conceptId: "{concepto}"}}) {{ id }} }}',
         "assignConceptToAccount", token)


def mover(token, cuenta, concepto, monto, fecha=None, descripcion=None):
    return dato(CREAR_MOV, "createTransaction", token,
                {"a": cuenta, "c": concepto, "m": monto, "f": fecha, "d": descripcion})


def preparar_referencia():
    e = nueva_empresa()
    t = e["token"]
    e["cuentas"] = {n: crear_cuenta(t, n) for n in ("Banco", "Caja", "Ahorro")}
    e["conceptos"] = {n: crear_concepto(t, n, tipo) for n, tipo in CONCEPTOS}
    for cuenta, conceptos in PERMITIDOS.items():
        for c in conceptos:
            permitir(t, e["cuentas"][cuenta], e["conceptos"][c])
    e["movimientos"] = []
    for cuenta, fecha, concepto, monto, desc in MOVIMIENTOS:
        m = mover(t, e["cuentas"][cuenta], e["conceptos"][concepto], monto, fecha, desc)
        e["movimientos"].append({"id": m["id"], "cuenta": cuenta, "importe": monto, "descripcion": desc})
    return e


if __name__ == "__main__":
    e = preparar_referencia()
    carpeta = os.path.join(os.path.dirname(__file__), "..", "actividad7", "variables")
    os.makedirs(carpeta, exist_ok=True)
    for nombre, cid in e["cuentas"].items():
        with open(os.path.join(carpeta, f"balance_{nombre.lower()}.json"), "w") as f:
            json.dump({"accountId": cid, "from": "2026-10-26", "to": "2026-10-30"}, f, indent=2)
            f.write("\n")
    with open(os.path.join(carpeta, "balance_banco_28.json"), "w") as f:
        json.dump({"accountId": e["cuentas"]["Banco"], "from": "2026-10-28", "to": "2026-10-28"}, f, indent=2)
        f.write("\n")
    with open(os.path.join(carpeta, "balance_general.json"), "w") as f:
        json.dump({"from": "2026-10-26", "to": "2026-10-30"}, f, indent=2)
        f.write("\n")
    with open(os.path.join(carpeta, "entrar.json"), "w") as f:
        json.dump({"email": f"admin.{e['sufijo'].lower()}@balances.test", "password": "lab123"}, f, indent=2)
        f.write("\n")
    with open(os.path.join(carpeta, "captura_con_fecha.json"), "w") as f:
        json.dump({"accountId": e["cuentas"]["Banco"], "conceptId": e["conceptos"]["Renta"],
                   "amount": "100.00", "date": "2026-10-27T12:00:00Z"}, f, indent=2)
        f.write("\n")
    print(f"Empresa {e['empresa']} - cuentas {e['cuentas']}")
    print("Correo del administrador: admin.%s@balances.test / contrasena de laboratorio: lab123" % e["sufijo"].lower())
    print("Variables escritas en actividad7/variables/")
