"""Unidad 3 Actividad 2: createTransaction idempotente.

Cada prueba usa una empresa nueva, asi no cambia los saldos de la demostracion.
Con el servidor arriba:

    python -m unittest -v tests.test_idempotencia
"""
import os
import sys
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pruebas"))

from jwt_lab import gql, error  # noqa: E402
from actividad7_datos import nueva_empresa, crear_cuenta, crear_concepto, permitir  # noqa: E402

PAGAR = """mutation($a: ID!, $c: ID!, $m: Decimal!, $k: String) {
  createTransaction(input: {accountId: $a, conceptId: $c, amount: $m, description: "Pago de renta",
                            idempotencyKey: $k}) { id amount }
}"""
MOVIMIENTOS = "{ transactions { id } }"
SALDOS = "{ accounts { id balance } }"


class IdempotenciaTest(unittest.TestCase):
    def setUp(self):
        e = nueva_empresa("Idempotencia Lab")
        self.token = e["token"]
        self.cuenta = crear_cuenta(self.token, "Banco")
        self.renta = crear_concepto(self.token, "Renta", "EXPENSE")
        permitir(self.token, self.cuenta, self.renta)

    def pagar(self, llave, monto="100.00"):
        return gql(PAGAR, {"a": self.cuenta, "c": self.renta, "m": monto, "k": llave}, self.token)

    def movimientos(self):
        return len(gql(MOVIMIENTOS, token=self.token)["data"]["transactions"])

    def saldo(self):
        return gql(SALDOS, token=self.token)["data"]["accounts"][0]["balance"]

    def test_misma_llave_mismo_movimiento(self):
        llave = str(uuid.uuid4())
        primero = self.pagar(llave)
        segundo = self.pagar(llave)
        self.assertIsNone(error(primero))
        self.assertIsNone(error(segundo))
        self.assertEqual(primero["data"]["createTransaction"]["id"], segundo["data"]["createTransaction"]["id"])
        self.assertEqual(self.movimientos(), 1)
        self.assertEqual(self.saldo(), "-100.00", "el balance se movio una sola vez")

    def test_otra_llave_otro_movimiento(self):
        a = self.pagar(str(uuid.uuid4()))["data"]["createTransaction"]["id"]
        b = self.pagar(str(uuid.uuid4()))["data"]["createTransaction"]["id"]
        self.assertNotEqual(a, b, "dos rentas de 100 con llaves distintas son dos movimientos")
        self.assertEqual(self.movimientos(), 2)
        self.assertEqual(self.saldo(), "-200.00")

    def test_misma_llave_otros_datos(self):
        llave = str(uuid.uuid4())
        self.pagar(llave, "100.00")
        r = self.pagar(llave, "250.00")
        self.assertEqual(error(r), "Esa idempotencyKey ya se uso con otros datos")
        self.assertEqual(self.movimientos(), 1)

    def test_reintentos_simultaneos(self):
        # Cinco envios al mismo tiempo con la misma llave: el indice unico deja una sola fila
        llave = str(uuid.uuid4())
        with ThreadPoolExecutor(max_workers=5) as pool:
            respuestas = list(pool.map(lambda _: self.pagar(llave), range(5)))
        ids = {r["data"]["createTransaction"]["id"] for r in respuestas if not error(r)}
        self.assertEqual(len(ids), 1, [error(r) for r in respuestas])
        self.assertEqual(self.movimientos(), 1)
        self.assertEqual(self.saldo(), "-100.00")

    def test_sin_llave_sigue_funcionando(self):
        # Compatibilidad con los scripts de la Unidad II: sin llave cada envio es un movimiento
        self.pagar(None)
        self.pagar(None)
        self.assertEqual(self.movimientos(), 2)

    def test_llave_corta(self):
        r = self.pagar("abc")
        self.assertIn("idempotencyKey", error(r))
        self.assertEqual(self.movimientos(), 0)


if __name__ == "__main__":
    unittest.main()
