"""E07: un fallo despues del flush y antes del commit revierte toda la lista.

Correr con la base del laboratorio arriba (el rol CAPTURISTA ya cargado):
    python -m unittest -v tests.test_e07_rollback
"""
import unittest
from unittest import mock

import configuracion
from database import SessionLocal
from models import RoleModel, PermissionModel, RolePermissionModel


def estado(db, role_id):
    filas = db.query(RolePermissionModel).filter(RolePermissionModel.role_id == role_id).all()
    return sorted((rp.id, rp.permission_id, rp.is_active) for rp in filas)


class RollbackTest(unittest.TestCase):
    def test_fallo_antes_del_commit(self):
        with SessionLocal() as db:
            rol = db.query(RoleModel).filter(RoleModel.code == "CAPTURISTA").one()
            antes = estado(db, rol.id)
            activos = [pid for _, pid, act in antes if act]
            # Lista distinta a la actual: quita un permiso y agrega concepts.write
            nuevo = db.query(PermissionModel).filter(PermissionModel.code == "concepts.write").one()
            deseada = [str(p) for p in activos[1:]] + [str(nuevo.id)]

        visto = {}
        real = configuracion.escribir_plan

        def escribir_y_fallar(db, plan):
            real(db, plan)  # hace flush: los UPDATE/INSERT ya llegaron a MySQL
            visto["dentro"] = estado(db, plan["role"].id)
            raise RuntimeError("fallo controlado despues del flush")

        with mock.patch.object(configuracion, "escribir_plan", escribir_y_fallar):
            with SessionLocal() as db:
                with self.assertRaises(RuntimeError):
                    configuracion.aplicar_lista(db, rol.id, deseada)

        self.assertNotEqual(visto["dentro"], antes, "dentro de la transaccion el estado si cambio")

        with SessionLocal() as nueva:
            self.assertEqual(estado(nueva, rol.id), antes, "despues del rollback quedo igual")


if __name__ == "__main__":
    unittest.main()
