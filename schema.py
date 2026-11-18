import hashlib
import json
import re
import secrets
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

import strawberry
from sqlalchemy.exc import IntegrityError

from auth import crear_token, leer_actor
from balances import CENTAVO, dinero, balance_cuenta, balance_general
from configuracion import PREFIJOS, validar_propuesta, calcular_plan, aplicar_lista
from database import SessionLocal
from models import (
    CompanyModel, UserModel, CompanyUserModel, AccountModel, ConceptModel, AccountConceptModel,
    TransactionModel, RoleModel, PermissionModel, RolePermissionModel, CompanyUserRoleModel,
    IdempotencyKeyModel,
)


def hashear(password: str) -> str:
    sal = secrets.token_hex(8)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), sal.encode(), 100_000).hex()
    return f"{sal}${h}"


def verificar(password: str, guardado: str) -> bool:
    sal, h = guardado.split("$")
    return hashlib.pbkdf2_hmac("sha256", password.encode(), sal.encode(), 100_000).hex() == h


def membresia_activa(db, company_user_id: int) -> CompanyUserModel:
    cu = db.get(CompanyUserModel, company_user_id)
    if cu is None or not cu.is_active:
        raise PermissionError("La membresia no existe o esta desactivada")
    return cu


def exigir_permiso(db, company_user_id: int, codigo: str) -> CompanyUserModel:
    cu = membresia_activa(db, company_user_id)
    asignacion = (
        db.query(CompanyUserRoleModel)
        .filter(
            CompanyUserRoleModel.company_user_id == company_user_id,
            CompanyUserRoleModel.is_active.is_(True),
        )
        .first()
    )
    if asignacion is None:
        raise PermissionError("La membresia no tiene un rol activo")

    permitido = (
        db.query(RolePermissionModel)
        .join(PermissionModel)
        .filter(
            RolePermissionModel.role_id == asignacion.role_id,
            RolePermissionModel.is_active.is_(True),
            PermissionModel.code == codigo,
            PermissionModel.is_active.is_(True),
        )
        .first()
    )
    if permitido is None:
        raise PermissionError(f"El rol no tiene el permiso {codigo}")
    return cu


def rol_de(db, company_user_id: int) -> Optional[RoleModel]:
    a = (
        db.query(CompanyUserRoleModel)
        .filter(CompanyUserRoleModel.company_user_id == company_user_id, CompanyUserRoleModel.is_active.is_(True))
        .first()
    )
    return a.role if a else None


def permisos_de(db, role_id: int) -> list[str]:
    filas = (
        db.query(PermissionModel.code)
        .join(RolePermissionModel, RolePermissionModel.permission_id == PermissionModel.id)
        .filter(
            RolePermissionModel.role_id == role_id,
            RolePermissionModel.is_active.is_(True),
            PermissionModel.is_active.is_(True),
        )
        .order_by(PermissionModel.code)
        .all()
    )
    return [f[0] for f in filas]


def asignar_rol(db, company_user_id: int, role_id: int) -> CompanyUserRoleModel:
    db.query(CompanyUserRoleModel).filter(
        CompanyUserRoleModel.company_user_id == company_user_id,
        CompanyUserRoleModel.is_active.is_(True),
    ).update({"is_active": False})
    nuevo = CompanyUserRoleModel(company_user_id=company_user_id, role_id=role_id, is_active=True)
    db.add(nuevo)
    return nuevo


@strawberry.enum
class TransactionType(Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


@strawberry.enum
class AccountType(Enum):
    CASH = "CASH"
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    SAVINGS = "SAVINGS"
    INVESTMENT = "INVESTMENT"
    WALLET = "WALLET"
    OTHER = "OTHER"


@strawberry.enum
class PermissionResource(Enum):
    COMPANY_USERS = "COMPANY_USERS"
    ACCOUNTS = "ACCOUNTS"
    CONCEPTS = "CONCEPTS"
    TRANSACTIONS = "TRANSACTIONS"
    ROLES = "ROLES"


@strawberry.type
class Company:
    id: strawberry.ID
    name: str
    rfc: str
    is_active: bool


@strawberry.type
class User:
    id: strawberry.ID
    name: str
    email: str
    is_active: bool


@strawberry.type
class Role:
    id: strawberry.ID
    code: str
    name: str
    description: Optional[str]
    is_active: bool


@strawberry.type
class Permission:
    id: strawberry.ID
    code: str
    name: str
    description: Optional[str]
    is_active: bool


@strawberry.type
class CompanyUser:
    id: strawberry.ID
    company_id: strawberry.ID
    user: User
    is_admin: bool
    is_active: bool
    role: Optional[Role]


@strawberry.type
class RolePermission:
    id: strawberry.ID
    role: Role
    permission: Permission
    is_active: bool


@strawberry.type
class CompanyUserRole:
    id: strawberry.ID
    company_user: CompanyUser
    role: Role
    is_active: bool


@strawberry.type
class Account:
    id: strawberry.ID
    company_id: strawberry.ID
    name: str
    balance: Decimal
    is_active: bool
    account_type: AccountType
    bank_name: Optional[str]
    # La CLABE completa no sale del API: solo los ultimos cuatro digitos
    clabe_masked: Optional[str]
    description: Optional[str]


@strawberry.type
class Concept:
    id: strawberry.ID
    company_id: strawberry.ID
    name: str
    type: TransactionType
    is_active: bool
    description: Optional[str]


@strawberry.type
class AccountConcept:
    id: strawberry.ID
    account_id: strawberry.ID
    concept_id: strawberry.ID
    is_active: bool
    concept: Concept


@strawberry.type
class Transaction:
    id: strawberry.ID
    company_id: strawberry.ID
    account_id: strawberry.ID
    concept_id: strawberry.ID
    captured_by: strawberry.ID
    type: TransactionType
    amount: Decimal
    description: Optional[str]
    created_at: datetime
    transaction_date: datetime
    captured_at: datetime
    is_active: bool


@strawberry.type
class AccountBalance:
    account_id: strawberry.ID
    account_name: str
    is_active: bool
    opening_balance: Decimal
    total_income: Decimal
    total_expense: Decimal
    profit: Decimal
    closing_balance: Decimal
    is_in_red: bool


@strawberry.type
class GeneralBalance:
    company_id: strawberry.ID
    currency: str
    from_date: date
    to_date: date
    opening_balance: Decimal
    total_income: Decimal
    total_expense: Decimal
    profit: Decimal
    closing_balance: Decimal
    is_in_red: bool
    accounts_in_red: int
    accounts: list[AccountBalance]


@strawberry.type
class RolePermissionPlan:
    role: Role
    current: list[Permission]
    to_activate: list[Permission]
    to_deactivate: list[Permission]
    unchanged: list[Permission]
    final_count: int


@strawberry.type
class RolePermissionUpdate:
    role: Role
    activated: list[Permission]
    deactivated: list[Permission]
    unchanged: list[Permission]
    final_count: int
    changed: bool


@strawberry.type
class SessionInfo:
    company_user_id: strawberry.ID
    company: Company
    user: User
    role: Optional[Role]
    # Unidad 3 Actividad 2: el dashboard decide que botones dibujar; el servidor sigue validando
    permissions: list[str]


@strawberry.type
class AuthPayload:
    token: str
    token_type: str
    user: User


def a_company(m): return Company(id=m.id, name=m.name, rfc=m.rfc, is_active=m.is_active)
def a_user(m): return User(id=m.id, name=m.name, email=m.email, is_active=m.is_active)
def a_role(m): return Role(id=m.id, code=m.code, name=m.name, description=m.description, is_active=m.is_active)
def a_perm(m): return Permission(id=m.id, code=m.code, name=m.name, description=m.description, is_active=m.is_active)
def a_rp(m): return RolePermission(id=m.id, role=a_role(m.role), permission=a_perm(m.permission), is_active=m.is_active)
def mascara_clabe(clabe):
    return f"•••• {clabe[-4:]}" if clabe else None


def a_account(m):
    return Account(id=m.id, company_id=m.company_id, name=m.name, balance=dinero(m.balance), is_active=m.is_active,
                   account_type=AccountType(m.account_type or "OTHER"), bank_name=m.bank_name,
                   clabe_masked=mascara_clabe(m.clabe), description=m.description)


def a_concept(m):
    return Concept(id=m.id, company_id=m.company_id, name=m.name, type=TransactionType(m.type),
                   is_active=m.is_active, description=m.description)


def a_ac(m):
    return AccountConcept(id=m.id, account_id=m.account_id, concept_id=m.concept_id, is_active=m.is_active,
                          concept=a_concept(m.concept))


def a_cu(db, m):
    r = rol_de(db, m.id)
    return CompanyUser(id=m.id, company_id=m.company_id, user=a_user(m.user), is_admin=m.is_admin,
                       is_active=m.is_active, role=a_role(r) if r else None)


def utc(d):
    # MySQL guarda la fecha sin zona; se devuelve marcada como UTC
    return d.replace(tzinfo=timezone.utc) if d is not None else None


def a_tx(m):
    return Transaction(id=m.id, company_id=m.company_id, account_id=m.account_id, concept_id=m.concept_id,
                       captured_by=m.company_user_id, type=TransactionType(m.type), amount=dinero(m.amount),
                       description=m.description, created_at=utc(m.created_at),
                       transaction_date=utc(m.transaction_date), captured_at=utc(m.captured_at),
                       is_active=m.is_active)


def leer_lector_balances(db, info):
    # Los balances son datos de cuentas y de movimientos: se piden los dos permisos
    actor_id = leer_actor(db, info)
    exigir_permiso(db, actor_id, "accounts.read")
    return exigir_permiso(db, actor_id, "transactions.read")


def texto(valor: Optional[str], campo: str, maximo: int, requerido: bool = False) -> Optional[str]:
    limpio = (valor or "").strip()
    if not limpio:
        if requerido:
            raise ValueError(f"{campo} es obligatorio")
        return None
    if len(limpio) > maximo:
        raise ValueError(f"{campo} no puede pasar de {maximo} caracteres")
    return limpio


CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def cuenta_de_empresa(db, actor, account_id) -> AccountModel:
    try:
        a = db.get(AccountModel, int(account_id))
    except ValueError:
        a = None
    if a is None or a.company_id != actor.company_id:
        raise ValueError("La cuenta no es de tu empresa")
    return a


# ---------- Idempotencia (Unidad 3 Actividad 2) ----------

OPERACION_MOVIMIENTO = "createTransaction"


def normalizar_llave(llave: Optional[str]) -> Optional[str]:
    if llave is None:
        return None
    limpia = llave.strip()
    if not 8 <= len(limpia) <= 100:
        raise ValueError("idempotencyKey tiene que tener entre 8 y 100 caracteres")
    return limpia


def huella_movimiento(input, monto: Decimal) -> str:
    # Hash del cuerpo tal como lo mando el cliente (no de lo que calcula el servidor,
    # como la fecha por omision, que cambiaria en cada reintento)
    fecha = input.transaction_date
    if fecha is not None and fecha.tzinfo is not None:
        fecha = fecha.astimezone(timezone.utc)
    cuerpo = {
        "accountId": str(input.account_id),
        "conceptId": str(input.concept_id),
        "amount": str(monto),
        "description": input.description,
        "transactionDate": fecha.isoformat() if fecha else None,
    }
    return hashlib.sha256(json.dumps(cuerpo, sort_keys=True).encode()).hexdigest()


def buscar_llave(db, company_id: int, llave: str) -> Optional[IdempotencyKeyModel]:
    return db.query(IdempotencyKeyModel).filter(
        IdempotencyKeyModel.company_id == company_id,
        IdempotencyKeyModel.operation == OPERACION_MOVIMIENTO,
        IdempotencyKeyModel.idem_key == llave,
    ).first()


def respuesta_guardada(db, guardada: IdempotencyKeyModel, huella: str):
    if guardada.request_hash != huella:
        raise ValueError("Esa idempotencyKey ya se uso con otros datos")
    return a_tx(db.get(TransactionModel, guardada.transaction_id))


MAXIMO = Decimal("9999999999.99")  # lo que cabe en Numeric(12, 2)


def validar_monto(monto: Decimal) -> Decimal:
    if not monto.is_finite():
        raise ValueError("El monto tiene que ser un numero finito")
    if monto <= 0:
        raise ValueError("El monto tiene que ser mayor a cero")
    if monto != monto.quantize(CENTAVO):
        raise ValueError("El monto no puede tener mas de dos decimales")
    if monto > MAXIMO:
        raise ValueError("El monto es mayor al maximo permitido")
    return monto.quantize(CENTAVO)


def fecha_operacion(valor: Optional[datetime]) -> datetime:
    if valor is None:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    if valor.tzinfo is None:
        raise ValueError("transactionDate tiene que llevar zona horaria, por ejemplo 2026-10-27T12:00:00Z")
    return valor.astimezone(timezone.utc).replace(tzinfo=None)


@strawberry.input
class CreateCompanyInput:
    name: str
    rfc: str


@strawberry.input
class CreateCompanyAdminInput:
    company_id: strawberry.ID
    name: str
    email: str
    password: str


@strawberry.input
class CreateCompanyUserInput:
    name: str
    email: str
    password: str


@strawberry.input
class LoginInput:
    email: str
    password: str
    company_id: Optional[strawberry.ID] = None


@strawberry.input
class CreateRoleInput:
    code: str
    name: str
    description: Optional[str] = None


@strawberry.input
class CreatePermissionInput:
    code: str
    name: str
    description: Optional[str] = None


@strawberry.input
class AssignPermissionToRoleInput:
    role_id: strawberry.ID
    permission_id: strawberry.ID


@strawberry.input
class AssignRoleInput:
    company_user_id: strawberry.ID
    role_id: strawberry.ID


@strawberry.input
class SetRolePermissionsInput:
    role_id: strawberry.ID
    permission_ids: list[strawberry.ID]


@strawberry.input
class CreateAccountInput:
    name: str
    account_type: AccountType = AccountType.OTHER
    bank_name: Optional[str] = None
    clabe: Optional[str] = None
    description: Optional[str] = None


@strawberry.input
class CreateConceptInput:
    name: str
    type: TransactionType
    description: Optional[str] = None


@strawberry.input
class AssignConceptToAccountInput:
    account_id: strawberry.ID
    concept_id: strawberry.ID


@strawberry.input
class CreateTransactionInput:
    account_id: strawberry.ID
    concept_id: strawberry.ID
    amount: Decimal
    description: Optional[str] = None
    transaction_date: Optional[datetime] = None
    # Unidad 3 Actividad 2: una llave por accion del cliente (por ejemplo un UUID al pulsar Guardar)
    idempotency_key: Optional[str] = None


@strawberry.type
class Query:
    @strawberry.field
    def companies(self) -> list[Company]:
        with SessionLocal() as db:
            return [a_company(c) for c in db.query(CompanyModel).order_by(CompanyModel.id).all()]

    @strawberry.field
    def my_session(self, info: strawberry.Info) -> SessionInfo:
        # Unidad 3: el dashboard muestra empresa, usuario y rol de quien tiene el token.
        # Solo valida el token; no pide permisos porque no devuelve datos financieros.
        with SessionLocal() as db:
            cu = db.get(CompanyUserModel, leer_actor(db, info))
            r = rol_de(db, cu.id)
            return SessionInfo(company_user_id=cu.id, company=a_company(cu.company), user=a_user(cu.user),
                               role=a_role(r) if r else None,
                               permissions=permisos_de(db, r.id) if r and r.is_active else [])

    @strawberry.field
    def company_users(self, info: strawberry.Info) -> list[CompanyUser]:
        with SessionLocal() as db:
            actor = exigir_permiso(db, leer_actor(db, info), "company.users.read")
            filas = db.query(CompanyUserModel).filter(CompanyUserModel.company_id == actor.company_id).all()
            return [a_cu(db, cu) for cu in filas]

    @strawberry.field
    def roles(self, active_only: Optional[bool] = None) -> list[Role]:
        with SessionLocal() as db:
            q = db.query(RoleModel)
            if active_only:
                q = q.filter(RoleModel.is_active.is_(True))
            return [a_role(r) for r in q.order_by(RoleModel.id).all()]

    @strawberry.field
    def role(self, id: strawberry.ID) -> Optional[Role]:
        with SessionLocal() as db:
            r = db.get(RoleModel, int(id))
            return a_role(r) if r else None

    @strawberry.field
    def permissions(self, active_only: Optional[bool] = None) -> list[Permission]:
        with SessionLocal() as db:
            q = db.query(PermissionModel)
            if active_only:
                q = q.filter(PermissionModel.is_active.is_(True))
            return [a_perm(p) for p in q.order_by(PermissionModel.id).all()]

    @strawberry.field
    def role_permissions(self, role_id: strawberry.ID) -> list[RolePermission]:
        with SessionLocal() as db:
            filas = (
                db.query(RolePermissionModel)
                .filter(RolePermissionModel.role_id == int(role_id), RolePermissionModel.is_active.is_(True))
                .order_by(RolePermissionModel.permission_id)
                .all()
            )
            return [a_rp(rp) for rp in filas]

    @strawberry.field
    def permission_catalog(self, info: strawberry.Info,
                           resource: Optional[PermissionResource] = None) -> list[Permission]:
        with SessionLocal() as db:
            exigir_permiso(db, leer_actor(db, info), "roles.read")
            q = db.query(PermissionModel).filter(PermissionModel.is_active.is_(True))
            if resource is not None:
                q = q.filter(PermissionModel.code.startswith(PREFIJOS[resource.value]))
            return [a_perm(p) for p in q.order_by(PermissionModel.code).all()]

    @strawberry.field
    def preview_role_permissions(self, input: SetRolePermissionsInput,
                                 info: strawberry.Info) -> Optional[RolePermissionPlan]:
        with SessionLocal() as db:
            exigir_permiso(db, leer_actor(db, info), "roles.read")
            rol, deseados = validar_propuesta(db, input.role_id, input.permission_ids)
            plan = calcular_plan(db, rol, deseados)
            return RolePermissionPlan(
                role=a_role(rol),
                current=[a_perm(p) for p in plan["current"]],
                to_activate=[a_perm(p) for p in plan["to_activate"]],
                to_deactivate=[a_perm(p) for p in plan["to_deactivate"]],
                unchanged=[a_perm(p) for p in plan["unchanged"]],
                final_count=plan["final_count"],
            )

    @strawberry.field
    def accounts(self, info: strawberry.Info, active_only: Optional[bool] = None) -> list[Account]:
        with SessionLocal() as db:
            actor = exigir_permiso(db, leer_actor(db, info), "accounts.read")
            q = db.query(AccountModel).filter(AccountModel.company_id == actor.company_id)
            if active_only:
                q = q.filter(AccountModel.is_active.is_(True))
            return [a_account(a) for a in q.order_by(AccountModel.id).all()]

    @strawberry.field
    def concepts(self, info: strawberry.Info, active_only: Optional[bool] = None) -> list[Concept]:
        with SessionLocal() as db:
            actor = exigir_permiso(db, leer_actor(db, info), "concepts.read")
            q = db.query(ConceptModel).filter(ConceptModel.company_id == actor.company_id)
            if active_only:
                q = q.filter(ConceptModel.is_active.is_(True))
            return [a_concept(c) for c in q.order_by(ConceptModel.id).all()]

    @strawberry.field
    def account_concepts(self, info: strawberry.Info, account_id: strawberry.ID,
                         active_only: Optional[bool] = True) -> list[AccountConcept]:
        # Conceptos permitidos en una cuenta. Por omision solo las relaciones activas.
        with SessionLocal() as db:
            actor = exigir_permiso(db, leer_actor(db, info), "concepts.read")
            cuenta = cuenta_de_empresa(db, actor, account_id)
            q = db.query(AccountConceptModel).filter(AccountConceptModel.account_id == cuenta.id)
            if active_only:
                q = q.filter(AccountConceptModel.is_active.is_(True))
            return [a_ac(ac) for ac in q.order_by(AccountConceptModel.id).all()]

    @strawberry.field
    def account_balance(self, info: strawberry.Info, account_id: strawberry.ID,
                        from_date: date, to_date: date) -> AccountBalance:
        with SessionLocal() as db:
            actor = leer_lector_balances(db, info)
            try:
                cuenta = int(account_id)
            except ValueError:
                raise ValueError("Cuenta no disponible")
            return AccountBalance(**balance_cuenta(db, actor.company_id, cuenta, from_date, to_date))

    @strawberry.field
    def general_balance(self, info: strawberry.Info, from_date: date, to_date: date) -> GeneralBalance:
        with SessionLocal() as db:
            actor = leer_lector_balances(db, info)
            g = balance_general(db, actor.company_id, from_date, to_date)
            g["accounts"] = [AccountBalance(**c) for c in g["accounts"]]
            return GeneralBalance(**g)

    @strawberry.field
    def transactions(self, info: strawberry.Info) -> list[Transaction]:
        with SessionLocal() as db:
            actor = exigir_permiso(db, leer_actor(db, info), "transactions.read")
            filas = db.query(TransactionModel).filter(TransactionModel.company_id == actor.company_id).order_by(TransactionModel.id).all()
            return [a_tx(t) for t in filas]


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_company(self, input: CreateCompanyInput) -> Company:
        with SessionLocal() as db:
            c = CompanyModel(name=input.name, rfc=input.rfc.upper())
            db.add(c)
            db.commit()
            db.refresh(c)
            return a_company(c)

    @strawberry.mutation
    def create_company_admin(self, input: CreateCompanyAdminInput) -> CompanyUser:
        with SessionLocal() as db:
            company_id = int(input.company_id)
            if db.get(CompanyModel, company_id) is None:
                raise ValueError("La empresa no existe")
            ya = db.query(CompanyUserModel).filter(
                CompanyUserModel.company_id == company_id, CompanyUserModel.is_admin.is_(True)
            ).first()
            if ya:
                raise ValueError("Esta empresa ya tiene un administrador principal")
            if db.query(UserModel).filter(UserModel.email == input.email).first():
                raise ValueError("Ese correo ya esta registrado")
            u = UserModel(name=input.name, email=input.email, password_hash=hashear(input.password))
            db.add(u)
            db.flush()
            cu = CompanyUserModel(company_id=company_id, user_id=u.id, is_admin=True)
            db.add(cu)
            db.flush()
            admin = db.query(RoleModel).filter(RoleModel.code == "ADMINISTRADOR").one()
            asignar_rol(db, cu.id, admin.id)
            db.commit()
            db.refresh(cu)
            return a_cu(db, cu)

    @strawberry.mutation
    def create_company_user(self, input: CreateCompanyUserInput, info: strawberry.Info) -> CompanyUser:
        with SessionLocal() as db:
            actor = exigir_permiso(db, leer_actor(db, info), "company.users.write")
            nombre = texto(input.name, "El nombre", 150, requerido=True)
            correo = texto(input.email, "El correo", 150, requerido=True).lower()
            if not CORREO.match(correo):
                raise ValueError("El correo no tiene un formato valido")
            if len(input.password or "") < 6:
                raise ValueError("La contrasena tiene que tener al menos 6 caracteres")
            if db.query(UserModel).filter(UserModel.email == correo).first():
                raise ValueError("Ese correo ya esta registrado")
            u = UserModel(name=nombre, email=correo, password_hash=hashear(input.password))
            db.add(u)
            db.flush()
            cu = CompanyUserModel(company_id=actor.company_id, user_id=u.id, is_admin=False)
            db.add(cu)
            db.commit()
            db.refresh(cu)
            return a_cu(db, cu)

    @strawberry.mutation
    def deactivate_company_user(self, info: strawberry.Info, company_user_id: strawberry.ID) -> CompanyUser:
        with SessionLocal() as db:
            actor = exigir_permiso(db, leer_actor(db, info), "company.users.write")
            cu = db.get(CompanyUserModel, int(company_user_id))
            if cu is None or cu.company_id != actor.company_id:
                raise ValueError("Esa membresia no es de tu empresa")
            if cu.is_admin:
                raise ValueError("No se puede desactivar al administrador principal")
            cu.is_active = False
            db.commit()
            db.refresh(cu)
            return a_cu(db, cu)

    @strawberry.mutation
    def login(self, input: LoginInput) -> AuthPayload:
        with SessionLocal() as db:
            u = db.query(UserModel).filter(UserModel.email == input.email).first()
            if u is None or not u.is_active or not verificar(input.password, u.password_hash):
                raise ValueError("Correo o contrasena incorrectos")
            q = db.query(CompanyUserModel).filter(
                CompanyUserModel.user_id == u.id, CompanyUserModel.is_active.is_(True)
            )
            if input.company_id is not None:
                q = q.filter(CompanyUserModel.company_id == int(input.company_id))
            membresias = q.all()
            if not membresias:
                raise ValueError("Correo o contrasena incorrectos")
            if len(membresias) > 1:
                raise ValueError("Perteneces a varias empresas: indica companyId")
            cu = membresias[0]
            # companyId sale de la fila de la membresia, no del cliente
            return AuthPayload(token=crear_token(cu.id, cu.company_id), token_type="bearer", user=a_user(u))

    @strawberry.mutation
    def create_role(self, input: CreateRoleInput) -> Role:
        with SessionLocal() as db:
            code = input.code.strip().upper()
            if db.query(RoleModel).filter(RoleModel.code == code).first():
                raise ValueError(f"Ya existe un rol con el codigo {code}")
            r = RoleModel(code=code, name=input.name, description=input.description)
            db.add(r)
            db.commit()
            db.refresh(r)
            return a_role(r)

    @strawberry.mutation
    def deactivate_role(self, id: strawberry.ID) -> Role:
        with SessionLocal() as db:
            r = db.get(RoleModel, int(id))
            if r is None:
                raise ValueError("El rol no existe")
            r.is_active = False
            db.commit()
            db.refresh(r)
            return a_role(r)

    @strawberry.mutation
    def create_permission(self, input: CreatePermissionInput) -> Permission:
        with SessionLocal() as db:
            code = input.code.strip().lower()
            if db.query(PermissionModel).filter(PermissionModel.code == code).first():
                raise ValueError(f"Ya existe un permiso con el codigo {code}")
            p = PermissionModel(code=code, name=input.name, description=input.description)
            db.add(p)
            db.commit()
            db.refresh(p)
            return a_perm(p)

    @strawberry.mutation
    def assign_permission_to_role(self, input: AssignPermissionToRoleInput, info: strawberry.Info) -> RolePermission:
        with SessionLocal() as db:
            exigir_permiso(db, leer_actor(db, info), "roles.write")
            role_id, perm_id = int(input.role_id), int(input.permission_id)
            if db.get(RoleModel, role_id) is None or db.get(PermissionModel, perm_id) is None:
                raise ValueError("El rol o el permiso no existe")
            ya = db.query(RolePermissionModel).filter(
                RolePermissionModel.role_id == role_id,
                RolePermissionModel.permission_id == perm_id,
                RolePermissionModel.is_active.is_(True),
            ).first()
            if ya:
                raise ValueError("Ese rol ya tiene ese permiso activo")
            rp = db.query(RolePermissionModel).filter(
                RolePermissionModel.role_id == role_id,
                RolePermissionModel.permission_id == perm_id,
            ).first()
            if rp:
                rp.is_active = True
            else:
                rp = RolePermissionModel(role_id=role_id, permission_id=perm_id)
                db.add(rp)
            db.commit()
            db.refresh(rp)
            return a_rp(rp)

    @strawberry.mutation
    def remove_permission_from_role(self, info: strawberry.Info, role_id: strawberry.ID, permission_id: strawberry.ID) -> bool:
        with SessionLocal() as db:
            exigir_permiso(db, leer_actor(db, info), "roles.write")
            n = db.query(RolePermissionModel).filter(
                RolePermissionModel.role_id == int(role_id),
                RolePermissionModel.permission_id == int(permission_id),
                RolePermissionModel.is_active.is_(True),
            ).update({"is_active": False})
            db.commit()
            return n > 0

    @strawberry.mutation
    def set_role_permissions(self, input: SetRolePermissionsInput,
                             info: strawberry.Info) -> Optional[RolePermissionUpdate]:
        with SessionLocal() as db:
            exigir_permiso(db, leer_actor(db, info), "roles.write")
            plan = aplicar_lista(db, input.role_id, input.permission_ids)
            return RolePermissionUpdate(
                role=a_role(plan["role"]),
                activated=[a_perm(p) for p in plan["to_activate"]],
                deactivated=[a_perm(p) for p in plan["to_deactivate"]],
                unchanged=[a_perm(p) for p in plan["unchanged"]],
                final_count=plan["final_count"],
                changed=bool(plan["to_activate"] or plan["to_deactivate"]),
            )

    @strawberry.mutation
    def assign_role(self, input: AssignRoleInput, info: strawberry.Info) -> CompanyUserRole:
        with SessionLocal() as db:
            actor = exigir_permiso(db, leer_actor(db, info), "roles.write")
            cu = db.get(CompanyUserModel, int(input.company_user_id))
            if cu is None or cu.company_id != actor.company_id or not cu.is_active:
                raise ValueError("Esa membresia no es de tu empresa o esta desactivada")
            r = db.get(RoleModel, int(input.role_id))
            if r is None or not r.is_active:
                raise ValueError("El rol no existe o esta desactivado")
            if cu.is_admin and r.code != "ADMINISTRADOR":
                raise ValueError("El administrador principal conserva el rol ADMINISTRADOR")
            nuevo = asignar_rol(db, cu.id, r.id)
            db.commit()
            db.refresh(nuevo)
            return CompanyUserRole(id=nuevo.id, company_user=a_cu(db, cu), role=a_role(r), is_active=nuevo.is_active)

    @strawberry.mutation
    def create_account(self, input: CreateAccountInput, info: strawberry.Info) -> Account:
        with SessionLocal() as db:
            actor = exigir_permiso(db, leer_actor(db, info), "accounts.write")
            nombre = texto(input.name, "El nombre de la cuenta", 100, requerido=True)
            banco = texto(input.bank_name, "El banco", 100)
            clabe = texto(input.clabe, "La CLABE", 18)
            if clabe is not None and not re.fullmatch(r"\d{18}", clabe):
                raise ValueError("La CLABE tiene que tener 18 digitos")
            a = AccountModel(company_id=actor.company_id, name=nombre, balance=0,
                             account_type=input.account_type.value, bank_name=banco, clabe=clabe,
                             description=texto(input.description, "La descripcion", 255))
            db.add(a)
            db.commit()
            db.refresh(a)
            return a_account(a)

    @strawberry.mutation
    def create_concept(self, input: CreateConceptInput, info: strawberry.Info) -> Concept:
        with SessionLocal() as db:
            actor = exigir_permiso(db, leer_actor(db, info), "concepts.write")
            nombre = texto(input.name, "El nombre del concepto", 100, requerido=True)
            c = ConceptModel(company_id=actor.company_id, name=nombre, type=input.type.value,
                             description=texto(input.description, "La descripcion", 255))
            db.add(c)
            db.commit()
            db.refresh(c)
            return a_concept(c)

    @strawberry.mutation
    def assign_concept_to_account(self, input: AssignConceptToAccountInput, info: strawberry.Info) -> AccountConcept:
        with SessionLocal() as db:
            actor = exigir_permiso(db, leer_actor(db, info), "concepts.write")
            a = db.get(AccountModel, int(input.account_id))
            c = db.get(ConceptModel, int(input.concept_id))
            if a is None or c is None or a.company_id != actor.company_id or c.company_id != actor.company_id:
                raise ValueError("La cuenta o el concepto no son de tu empresa")
            ya = db.query(AccountConceptModel).filter(
                AccountConceptModel.account_id == a.id, AccountConceptModel.concept_id == c.id,
                AccountConceptModel.is_active.is_(True),
            ).first()
            if ya:
                raise ValueError("Ese concepto ya esta asignado a la cuenta")
            # Si la pareja se quito antes, se reactiva la misma fila en lugar de crear otra
            ac = db.query(AccountConceptModel).filter(
                AccountConceptModel.account_id == a.id, AccountConceptModel.concept_id == c.id,
            ).first()
            if ac:
                ac.is_active = True
            else:
                ac = AccountConceptModel(account_id=a.id, concept_id=c.id)
                db.add(ac)
            db.commit()
            db.refresh(ac)
            return a_ac(ac)

    @strawberry.mutation
    def remove_concept_from_account(self, input: AssignConceptToAccountInput, info: strawberry.Info) -> AccountConcept:
        # Baja logica de la relacion: no toca el catalogo de conceptos ni los movimientos viejos
        with SessionLocal() as db:
            actor = exigir_permiso(db, leer_actor(db, info), "concepts.write")
            a = cuenta_de_empresa(db, actor, input.account_id)
            ac = db.query(AccountConceptModel).filter(
                AccountConceptModel.account_id == a.id,
                AccountConceptModel.concept_id == int(input.concept_id),
                AccountConceptModel.is_active.is_(True),
            ).first()
            if ac is None:
                raise ValueError("Ese concepto no esta asignado a la cuenta")
            ac.is_active = False
            db.commit()
            db.refresh(ac)
            return a_ac(ac)

    @strawberry.mutation
    def create_transaction(self, input: CreateTransactionInput, info: strawberry.Info) -> Transaction:
        with SessionLocal() as db:
            actor = membresia_activa(db, leer_actor(db, info))
            monto = validar_monto(input.amount)
            llave = normalizar_llave(input.idempotency_key)
            huella = huella_movimiento(input, monto)
            if llave is not None:
                # Reintento: la llave ya esta en MySQL -> misma respuesta, sin otro INSERT
                exigir_permiso(db, actor.id, "transactions.write")
                guardada = buscar_llave(db, actor.company_id, llave)
                if guardada is not None:
                    return respuesta_guardada(db, guardada, huella)
            cuando = fecha_operacion(input.transaction_date)
            a = db.get(AccountModel, int(input.account_id))
            c = db.get(ConceptModel, int(input.concept_id))
            if a is None or c is None or a.company_id != actor.company_id or c.company_id != actor.company_id:
                raise ValueError("La cuenta o el concepto no son de tu empresa")
            permitido = db.query(AccountConceptModel).filter(
                AccountConceptModel.account_id == a.id, AccountConceptModel.concept_id == c.id,
                AccountConceptModel.is_active.is_(True),
            ).first()
            if permitido is None:
                raise ValueError("Ese concepto no esta permitido en esta cuenta")
            exigir_permiso(db, actor.id, "transactions.write")
            t = TransactionModel(company_id=actor.company_id, account_id=a.id, concept_id=c.id,
                                 company_user_id=actor.id, type=c.type, amount=monto,
                                 description=input.description, transaction_date=cuando)
            # captured_at lo pone el servidor (default); el cliente no lo elige
            a.balance = a.balance + monto if c.type == "INCOME" else a.balance - monto
            db.add(t)
            try:
                if llave is not None:
                    db.flush()  # para conocer t.id
                    # La llave y el movimiento van en la misma transaccion: un solo COMMIT
                    db.add(IdempotencyKeyModel(company_id=actor.company_id, operation=OPERACION_MOVIMIENTO,
                                               idem_key=llave, request_hash=huella, transaction_id=t.id,
                                               company_user_id=actor.id))
                db.commit()
            except IntegrityError:
                # Dos peticiones con la misma llave al mismo tiempo: el indice unico rechazo la segunda.
                # Se deshace este movimiento y se devuelve el que si quedo guardado.
                db.rollback()
                guardada = buscar_llave(db, actor.company_id, llave) if llave else None
                if guardada is None:
                    raise
                return respuesta_guardada(db, guardada, huella)
            db.refresh(t)
            return a_tx(t)


schema = strawberry.Schema(query=Query, mutation=Mutation)
