from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text
from strawberry.fastapi import GraphQLRouter

from database import Base, engine, SessionLocal
from models import RoleModel, PermissionModel, RolePermissionModel
from schema import schema

ROLES = [
    ("ADMINISTRADOR", "Administrador", "El administrador principal de la empresa"),
    ("CONTADOR", "Contador", "Arma cuentas y conceptos"),
    ("CAPTURISTA", "Capturista", "Registra movimientos"),
    ("CONSULTA", "Consulta", "Solo lee"),
]

PERMISOS = [
    ("company.users.read", "Ver membresias", "Ver las membresias de la empresa"),
    ("company.users.write", "Administrar membresias", "Crear usuarios y desactivar membresias"),
    ("accounts.read", "Ver cuentas", "Consultar cuentas"),
    ("accounts.write", "Crear cuentas", "Crear cuentas"),
    ("concepts.read", "Ver conceptos", "Consultar conceptos"),
    ("concepts.write", "Crear conceptos", "Crear conceptos y asignarlos a una cuenta"),
    ("transactions.read", "Ver movimientos", "Consultar movimientos"),
    ("transactions.write", "Registrar movimientos", "Registrar un ingreso o un egreso"),
    ("roles.read", "Ver roles", "Ver roles y la matriz de permisos"),
    ("roles.write", "Administrar roles", "Asignar o quitar permisos de un rol y asignar un rol a una membresia"),
]

MATRIZ = {
    "ADMINISTRADOR": [p[0] for p in PERMISOS],
    "CONTADOR": ["company.users.read", "accounts.read", "accounts.write", "concepts.read", "concepts.write",
                 "transactions.read", "transactions.write", "roles.read"],
    "CAPTURISTA": ["accounts.read", "concepts.read", "transactions.read", "transactions.write"],
    "CONSULTA": ["company.users.read", "accounts.read", "concepts.read", "transactions.read"],
}


def carga_inicial():
    with SessionLocal() as db:
        if db.query(RoleModel).count() == 0:
            for code, name, desc in ROLES:
                db.add(RoleModel(code=code, name=name, description=desc))
        if db.query(PermissionModel).count() == 0:
            for code, name, desc in PERMISOS:
                db.add(PermissionModel(code=code, name=name, description=desc))
        db.commit()

        permisos = {p.code: p.id for p in db.query(PermissionModel).all()}
        for rol in db.query(RoleModel).filter(RoleModel.code.in_(MATRIZ.keys())).all():
            if db.query(RolePermissionModel).filter(RolePermissionModel.role_id == rol.id).count() == 0:
                for code in MATRIZ[rol.code]:
                    db.add(RolePermissionModel(role_id=rol.id, permission_id=permisos[code]))
        db.commit()


def migrar():
    # create_all no cambia tablas que ya existen; ver migraciones/001_unique_role_permissions.sql
    with engine.begin() as con:
        hay = con.execute(text(
            "SELECT COUNT(*) FROM information_schema.statistics "
            "WHERE table_schema = DATABASE() AND table_name = 'role_permissions' AND index_name = 'uq_role_permission'"
        )).scalar()
        if not hay:
            con.execute(text("ALTER TABLE role_permissions ADD CONSTRAINT uq_role_permission UNIQUE (role_id, permission_id)"))

        # Actividad 7: fecha de operacion, fecha de captura y estado del movimiento
        # (ver migraciones/002_transaction_dates.sql)
        columnas = set(con.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = 'transactions'"
        )).scalars())
        if "transaction_date" not in columnas:
            con.execute(text("ALTER TABLE transactions ADD COLUMN transaction_date DATETIME NULL"))
            con.execute(text("UPDATE transactions SET transaction_date = created_at"))
            con.execute(text("ALTER TABLE transactions MODIFY transaction_date DATETIME NOT NULL"))
        if "captured_at" not in columnas:
            con.execute(text("ALTER TABLE transactions ADD COLUMN captured_at DATETIME NULL"))
            con.execute(text("UPDATE transactions SET captured_at = created_at"))
            con.execute(text("ALTER TABLE transactions MODIFY captured_at DATETIME NOT NULL"))
        if "is_active" not in columnas:
            con.execute(text("ALTER TABLE transactions ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"))
        hay = con.execute(text(
            "SELECT COUNT(*) FROM information_schema.statistics "
            "WHERE table_schema = DATABASE() AND table_name = 'transactions' AND index_name = 'ix_transactions_account_date'"
        )).scalar()
        if not hay:
            con.execute(text("CREATE INDEX ix_transactions_account_date ON transactions (account_id, transaction_date)"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    migrar()
    carga_inicial()
    yield


app = FastAPI(title="Sistema General de Ingresos", lifespan=lifespan)
app.include_router(GraphQLRouter(schema), prefix="/graphql")


@app.get("/")
def inicio():
    return {"mensaje": "Sistema General de Ingresos, entra a /graphql"}
