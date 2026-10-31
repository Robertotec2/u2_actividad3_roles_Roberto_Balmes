"""Calculo de balances a partir de los movimientos (Actividad 7).

No hay tabla ni columna de balances: cada consulta suma en MySQL los movimientos activos
por su transaction_date. Todas las cantidades son MXN y las fechas se manejan en UTC.
"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import and_, case, func

from models import AccountModel, TransactionModel

CERO = Decimal("0.00")
CENTAVO = Decimal("0.01")
MONEDA = "MXN"


def dinero(valor) -> Decimal:
    d = Decimal(valor if valor is not None else 0).quantize(CENTAVO)
    return CERO if d == 0 else d


def limites(from_date: date, to_date: date) -> tuple[datetime, datetime]:
    """Dias completos en UTC: [from_date 00:00, dia siguiente a to_date 00:00)."""
    if from_date > to_date:
        raise ValueError("fromDate no puede ser posterior a toDate")
    inicio = datetime.combine(from_date, time.min)
    fin = datetime.combine(to_date + timedelta(days=1), time.min)
    return inicio, fin


def balances_por_cuenta(db, company_id: int, from_date: date, to_date: date, account_id: int | None = None) -> list[dict]:
    inicio, fin = limites(from_date, to_date)
    T = TransactionModel

    con_signo = case((T.type == "INCOME", T.amount), else_=-T.amount)
    en_periodo = T.transaction_date >= inicio
    saldo_inicial = func.coalesce(func.sum(case((T.transaction_date < inicio, con_signo))), 0)
    ingresos = func.coalesce(func.sum(case((and_(en_periodo, T.type == "INCOME"), T.amount))), 0)
    egresos = func.coalesce(func.sum(case((and_(en_periodo, T.type == "EXPENSE"), T.amount))), 0)

    # Los filtros del movimiento van en el ON del LEFT JOIN, no en el WHERE:
    # asi una cuenta sin movimientos sigue apareciendo con ceros.
    q = (
        db.query(AccountModel.id, AccountModel.name, AccountModel.is_active, saldo_inicial, ingresos, egresos)
        .outerjoin(T, and_(
            T.account_id == AccountModel.id,
            T.company_id == AccountModel.company_id,
            T.is_active.is_(True),
            T.transaction_date < fin,
        ))
        .filter(AccountModel.company_id == company_id)
    )
    if account_id is not None:
        q = q.filter(AccountModel.id == account_id)
    filas = q.group_by(AccountModel.id, AccountModel.name, AccountModel.is_active).order_by(AccountModel.id).all()

    resultado = []
    for cid, nombre, activa, inicial, ing, egr in filas:
        inicial, ing, egr = dinero(inicial), dinero(ing), dinero(egr)
        profit = dinero(ing - egr)
        final = dinero(inicial + profit)
        resultado.append({
            "account_id": cid,
            "account_name": nombre,
            "is_active": activa,
            "opening_balance": inicial,
            "total_income": ing,
            "total_expense": egr,
            "profit": profit,
            "closing_balance": final,
            "is_in_red": final < 0,
        })
    return resultado


def balance_cuenta(db, company_id: int, account_id: int, from_date: date, to_date: date) -> dict:
    filas = balances_por_cuenta(db, company_id, from_date, to_date, account_id)
    if not filas:
        # Inexistente o de otra empresa: el mismo mensaje, sin datos
        raise ValueError("Cuenta no disponible")
    return filas[0]


def balance_general(db, company_id: int, from_date: date, to_date: date) -> dict:
    cuentas = balances_por_cuenta(db, company_id, from_date, to_date)

    def total(campo):
        return dinero(sum((c[campo] for c in cuentas), CERO))

    final = total("closing_balance")
    return {
        "company_id": company_id,
        "currency": MONEDA,
        "from_date": from_date,
        "to_date": to_date,
        "opening_balance": total("opening_balance"),
        "total_income": total("total_income"),
        "total_expense": total("total_expense"),
        "profit": total("profit"),
        "closing_balance": final,
        "is_in_red": final < 0,
        "accounts_in_red": sum(1 for c in cuentas if c["is_in_red"]),
        "accounts": cuentas,
    }
