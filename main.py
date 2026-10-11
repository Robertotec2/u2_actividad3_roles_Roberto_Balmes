from contextlib import asynccontextmanager

from fastapi import FastAPI
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    carga_inicial()
    yield


app = FastAPI(title="Sistema General de Ingresos", lifespan=lifespan)
app.include_router(GraphQLRouter(schema), prefix="/graphql")


@app.get("/")
def inicio():
    return {"mensaje": "Sistema General de Ingresos, entra a /graphql"}
