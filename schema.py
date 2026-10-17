import hashlib
import secrets
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

import strawberry

from database import SessionLocal
from models import (
    CompanyModel, UserModel, CompanyUserModel, AccountModel, ConceptModel, AccountConceptModel,
    TransactionModel, RoleModel, PermissionModel, RolePermissionModel, CompanyUserRoleModel,
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
    balance: float
    is_active: bool


@strawberry.type
class Concept:
    id: strawberry.ID
    company_id: strawberry.ID
    name: str
    type: TransactionType
    is_active: bool


@strawberry.type
class AccountConcept:
    id: strawberry.ID
    account_id: strawberry.ID
    concept_id: strawberry.ID
    is_active: bool


@strawberry.type
class Transaction:
    id: strawberry.ID
    company_id: strawberry.ID
    account_id: strawberry.ID
    concept_id: strawberry.ID
    captured_by: strawberry.ID
    type: TransactionType
    amount: float
    description: Optional[str]
    created_at: datetime


@strawberry.type
class LoginPayload:
    token: str
    user: User


def a_company(m): return Company(id=m.id, name=m.name, rfc=m.rfc, is_active=m.is_active)
def a_user(m): return User(id=m.id, name=m.name, email=m.email, is_active=m.is_active)
def a_role(m): return Role(id=m.id, code=m.code, name=m.name, description=m.description, is_active=m.is_active)
def a_perm(m): return Permission(id=m.id, code=m.code, name=m.name, description=m.description, is_active=m.is_active)
def a_rp(m): return RolePermission(id=m.id, role=a_role(m.role), permission=a_perm(m.permission), is_active=m.is_active)
def a_account(m): return Account(id=m.id, company_id=m.company_id, name=m.name, balance=float(m.balance), is_active=m.is_active)
def a_concept(m): return Concept(id=m.id, company_id=m.company_id, name=m.name, type=TransactionType(m.type), is_active=m.is_active)
def a_ac(m): return AccountConcept(id=m.id, account_id=m.account_id, concept_id=m.concept_id, is_active=m.is_active)


def a_cu(db, m):
    r = rol_de(db, m.id)
    return CompanyUser(id=m.id, company_id=m.company_id, user=a_user(m.user), is_admin=m.is_admin,
                       is_active=m.is_active, role=a_role(r) if r else None)


def a_tx(m):
    return Transaction(id=m.id, company_id=m.company_id, account_id=m.account_id, concept_id=m.concept_id,
                       captured_by=m.company_user_id, type=TransactionType(m.type), amount=float(m.amount),
                       description=m.description, created_at=m.created_at)


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
    actor_company_user_id: strawberry.ID
    name: str
    email: str
    password: str


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
    actor_company_user_id: strawberry.ID
    role_id: strawberry.ID
    permission_id: strawberry.ID


@strawberry.input
class AssignRoleInput:
    actor_company_user_id: strawberry.ID
    company_user_id: strawberry.ID
    role_id: strawberry.ID


@strawberry.input
class CreateAccountInput:
    actor_company_user_id: strawberry.ID
    name: str


@strawberry.input
class CreateConceptInput:
    actor_company_user_id: strawberry.ID
    name: str
    type: TransactionType


@strawberry.input
class AssignConceptToAccountInput:
    actor_company_user_id: strawberry.ID
    account_id: strawberry.ID
    concept_id: strawberry.ID


@strawberry.input
class CreateTransactionInput:
    actor_company_user_id: strawberry.ID
    account_id: strawberry.ID
    concept_id: strawberry.ID
    amount: Decimal
    description: Optional[str] = None


@strawberry.type
class Query:
    @strawberry.field
    def companies(self) -> list[Company]:
        with SessionLocal() as db:
            return [a_company(c) for c in db.query(CompanyModel).order_by(CompanyModel.id).all()]

    @strawberry.field
    def company_users(self, actor_company_user_id: strawberry.ID) -> list[CompanyUser]:
        with SessionLocal() as db:
            actor = exigir_permiso(db, int(actor_company_user_id), "company.users.read")
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
    def accounts(self, actor_company_user_id: strawberry.ID) -> list[Account]:
        with SessionLocal() as db:
            actor = exigir_permiso(db, int(actor_company_user_id), "accounts.read")
            return [a_account(a) for a in db.query(AccountModel).filter(AccountModel.company_id == actor.company_id).all()]

    @strawberry.field
    def concepts(self, actor_company_user_id: strawberry.ID) -> list[Concept]:
        with SessionLocal() as db:
            actor = exigir_permiso(db, int(actor_company_user_id), "concepts.read")
            return [a_concept(c) for c in db.query(ConceptModel).filter(ConceptModel.company_id == actor.company_id).all()]

    @strawberry.field
    def transactions(self, actor_company_user_id: strawberry.ID) -> list[Transaction]:
        with SessionLocal() as db:
            actor = exigir_permiso(db, int(actor_company_user_id), "transactions.read")
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
    def create_company_user(self, input: CreateCompanyUserInput) -> CompanyUser:
        with SessionLocal() as db:
            actor = exigir_permiso(db, int(input.actor_company_user_id), "company.users.write")
            if db.query(UserModel).filter(UserModel.email == input.email).first():
                raise ValueError("Ese correo ya esta registrado")
            u = UserModel(name=input.name, email=input.email, password_hash=hashear(input.password))
            db.add(u)
            db.flush()
            cu = CompanyUserModel(company_id=actor.company_id, user_id=u.id, is_admin=False)
            db.add(cu)
            db.commit()
            db.refresh(cu)
            return a_cu(db, cu)

    @strawberry.mutation
    def deactivate_company_user(self, actor_company_user_id: strawberry.ID, company_user_id: strawberry.ID) -> CompanyUser:
        with SessionLocal() as db:
            actor = exigir_permiso(db, int(actor_company_user_id), "company.users.write")
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
    def login(self, email: str, password: str) -> LoginPayload:
        with SessionLocal() as db:
            u = db.query(UserModel).filter(UserModel.email == email).first()
            if u is None or not u.is_active or not verificar(password, u.password_hash):
                raise ValueError("Correo o contrasena incorrectos")
            return LoginPayload(token=secrets.token_urlsafe(32), user=a_user(u))

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
    def assign_permission_to_role(self, input: AssignPermissionToRoleInput) -> RolePermission:
        with SessionLocal() as db:
            exigir_permiso(db, int(input.actor_company_user_id), "roles.write")
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
    def remove_permission_from_role(self, actor_company_user_id: strawberry.ID, role_id: strawberry.ID, permission_id: strawberry.ID) -> bool:
        with SessionLocal() as db:
            exigir_permiso(db, int(actor_company_user_id), "roles.write")
            n = db.query(RolePermissionModel).filter(
                RolePermissionModel.role_id == int(role_id),
                RolePermissionModel.permission_id == int(permission_id),
                RolePermissionModel.is_active.is_(True),
            ).update({"is_active": False})
            db.commit()
            return n > 0

    @strawberry.mutation
    def assign_role(self, input: AssignRoleInput) -> CompanyUserRole:
        with SessionLocal() as db:
            actor = exigir_permiso(db, int(input.actor_company_user_id), "roles.write")
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
    def create_account(self, input: CreateAccountInput) -> Account:
        with SessionLocal() as db:
            actor = exigir_permiso(db, int(input.actor_company_user_id), "accounts.write")
            a = AccountModel(company_id=actor.company_id, name=input.name, balance=0)
            db.add(a)
            db.commit()
            db.refresh(a)
            return a_account(a)

    @strawberry.mutation
    def create_concept(self, input: CreateConceptInput) -> Concept:
        with SessionLocal() as db:
            actor = exigir_permiso(db, int(input.actor_company_user_id), "concepts.write")
            c = ConceptModel(company_id=actor.company_id, name=input.name, type=input.type.value)
            db.add(c)
            db.commit()
            db.refresh(c)
            return a_concept(c)

    @strawberry.mutation
    def assign_concept_to_account(self, input: AssignConceptToAccountInput) -> AccountConcept:
        with SessionLocal() as db:
            actor = exigir_permiso(db, int(input.actor_company_user_id), "concepts.write")
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
            ac = AccountConceptModel(account_id=a.id, concept_id=c.id)
            db.add(ac)
            db.commit()
            db.refresh(ac)
            return a_ac(ac)

    @strawberry.mutation
    def create_transaction(self, input: CreateTransactionInput) -> Transaction:
        with SessionLocal() as db:
            if input.amount <= 0:
                raise ValueError("El monto tiene que ser mayor a cero")
            actor = membresia_activa(db, int(input.actor_company_user_id))
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
                                 company_user_id=actor.id, type=c.type, amount=input.amount,
                                 description=input.description)
            a.balance = a.balance + input.amount if c.type == "INCOME" else a.balance - input.amount
            db.add(t)
            db.commit()
            db.refresh(t)
            return a_tx(t)


schema = strawberry.Schema(query=Query, mutation=Mutation)
