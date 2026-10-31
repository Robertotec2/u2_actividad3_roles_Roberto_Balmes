"""Actividad 7: pruebas automatizadas B01, B04, B06 y B12 contra la API y la base de prueba.

Los resultados esperados estan escritos a mano a partir de la tabla de referencia; no se usa
balances.py para calcularlos. Solo usa la biblioteca estandar (urllib), con el servidor arriba:

    python -m unittest -v tests.test_balances
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pruebas"))

from jwt_lab import gql, error  # noqa: E402
from actividad7_datos import (  # noqa: E402
    preparar_referencia, nueva_empresa, crear_cuenta, crear_concepto, permitir, mover,
)

CAMPOS = "accountId accountName isActive openingBalance totalIncome totalExpense profit closingBalance isInRed"
CUENTA = f"""query($id: ID!, $from: Date!, $to: Date!) {{
  accountBalance(accountId: $id, fromDate: $from, toDate: $to) {{ {CAMPOS} }}
}}"""
GENERAL = f"""query($from: Date!, $to: Date!) {{
  generalBalance(fromDate: $from, toDate: $to) {{
    companyId currency fromDate toDate openingBalance totalIncome totalExpense profit closingBalance
    isInRed accountsInRed accounts {{ {CAMPOS} }}
  }}
}}"""
MOVIMIENTOS = "{ transactions { id accountId type amount transactionDate capturedAt isActive } }"

# Tabla calculada a mano para el 26 al 30 de octubre de 2026
ESPERADO = {
    "Banco": ("1000.00", "3000.00", "2200.00", "800.00", "1800.00", False),
    "Caja": ("0.00", "500.00", "700.00", "-200.00", "-200.00", True),
    "Ahorro": ("0.00", "0.00", "0.00", "0.00", "0.00", False),
}
GENERAL_ESPERADO = ("1000.00", "3500.00", "2900.00", "600.00", "1600.00", False)


def cuenta(token, cid, desde="2026-10-26", hasta="2026-10-30"):
    return gql(CUENTA, {"id": cid, "from": desde, "to": hasta}, token)


def general(token, desde="2026-10-26", hasta="2026-10-30"):
    return gql(GENERAL, {"from": desde, "to": hasta}, token)


def cifras(b):
    return (b["openingBalance"], b["totalIncome"], b["totalExpense"], b["profit"], b["closingBalance"], b["isInRed"])


class B01Referencia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = preparar_referencia()
        cls.t = cls.e["token"]

    def test_cada_cuenta_coincide_con_la_tabla(self):
        for nombre, esperado in ESPERADO.items():
            with self.subTest(cuenta=nombre):
                r = cuenta(self.t, self.e["cuentas"][nombre])
                self.assertIsNone(error(r))
                b = r["data"]["accountBalance"]
                self.assertEqual(b["accountName"], nombre)
                self.assertEqual(cifras(b), esperado)

    def test_general_coincide_y_cuadra_con_el_detalle(self):
        g = general(self.t)["data"]["generalBalance"]
        self.assertEqual(cifras(g), GENERAL_ESPERADO)
        self.assertEqual(g["currency"], "MXN")
        self.assertEqual(g["accountsInRed"], 1)
        self.assertEqual([a["accountName"] for a in g["accounts"]], ["Banco", "Caja", "Ahorro"])
        ids = [int(a["accountId"]) for a in g["accounts"]]
        self.assertEqual(ids, sorted(ids))
        for a in g["accounts"]:
            self.assertEqual(cifras(a), ESPERADO[a["accountName"]])

    def test_consultar_no_cambia_filas(self):
        antes = gql(MOVIMIENTOS, token=self.t)["data"]["transactions"]
        cuenta(self.t, self.e["cuentas"]["Banco"])
        general(self.t)
        self.assertEqual(gql(MOVIMIENTOS, token=self.t)["data"]["transactions"], antes)
        self.assertEqual(len(antes), 6)


class B04Limites(unittest.TestCase):
    def test_limites_de_dias_completos_en_utc(self):
        e = nueva_empresa()
        t = e["token"]
        c = crear_cuenta(t, "Limites")
        k = crear_concepto(t, "Deposito", "INCOME")
        permitir(t, c, k)
        mover(t, c, k, "1.00", "2026-10-25T23:59:59Z")   # antes del inicio: solo saldo inicial
        mover(t, c, k, "10.00", "2026-10-26T00:00:00Z")  # justo en el inicio: dentro
        mover(t, c, k, "100.00", "2026-10-30T23:59:59Z")  # final del dia 30: dentro
        mover(t, c, k, "1000.00", "2026-10-31T00:00:00Z")  # medianoche del 31: fuera
        b = cuenta(t, c)["data"]["accountBalance"]
        self.assertEqual(b["openingBalance"], "1.00")
        self.assertEqual(b["totalIncome"], "110.00")
        self.assertEqual(b["closingBalance"], "111.00")
        # El del 31 si entra al consultar el 31
        b31 = cuenta(t, c, "2026-10-31", "2026-10-31")["data"]["accountBalance"]
        self.assertEqual((b31["openingBalance"], b31["totalIncome"]), ("111.00", "1000.00"))


class B06Centavos(unittest.TestCase):
    def test_decimales_exactos(self):
        e = nueva_empresa()
        t = e["token"]
        c = crear_cuenta(t, "Centavos")
        i = crear_concepto(t, "Entrada", "INCOME")
        g = crear_concepto(t, "Salida", "EXPENSE")
        permitir(t, c, i)
        permitir(t, c, g)
        mover(t, c, i, "0.10", "2026-10-27T12:00:00Z")
        mover(t, c, i, "0.20", "2026-10-27T12:00:00Z")
        mover(t, c, g, "0.30", "2026-10-27T12:00:00Z")
        b = cuenta(t, c)["data"]["accountBalance"]
        self.assertEqual((b["totalIncome"], b["totalExpense"]), ("0.30", "0.30"))
        self.assertEqual((b["profit"], b["closingBalance"], b["isInRed"]), ("0.00", "0.00", False))


class B12OtraEmpresa(unittest.TestCase):
    def test_token_de_a_no_ve_cuentas_de_b(self):
        a = preparar_referencia()
        b = preparar_referencia()
        ajena = b["cuentas"]["Banco"]

        r = cuenta(a["token"], ajena)
        self.assertEqual(error(r), "Cuenta no disponible")
        self.assertIsNone(r["data"])
        self.assertNotIn("1800.00", str(r))

        # Una cuenta inexistente responde exactamente igual
        self.assertEqual(error(cuenta(a["token"], "999999")), "Cuenta no disponible")

        g = general(a["token"])["data"]["generalBalance"]
        self.assertEqual(g["companyId"], a["empresa"])
        self.assertEqual(sorted(x["accountId"] for x in g["accounts"]), sorted(a["cuentas"].values()))


if __name__ == "__main__":
    unittest.main()
