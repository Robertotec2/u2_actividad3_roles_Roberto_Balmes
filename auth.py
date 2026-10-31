import os
from datetime import datetime, timedelta, timezone

import jwt

from models import CompanyUserModel

VIGENCIA = timedelta(minutes=30)


def secreto() -> str:
    # El secreto vive en el ambiente (JWT_SECRET), nunca en el codigo ni en Git
    valor = os.getenv("JWT_SECRET")
    if not valor:
        raise RuntimeError("Falta la variable de ambiente JWT_SECRET")
    return valor


def crear_token(company_user_id: int, company_id: int) -> str:
    ahora = datetime.now(timezone.utc)
    datos = {
        "companyUserId": company_user_id,
        "companyId": company_id,
        "exp": ahora + VIGENCIA,
    }
    return jwt.encode(datos, secreto(), algorithm="HS256")


def leer_actor(db, info) -> int:
    encabezado = info.context["request"].headers.get("authorization", "")
    if not encabezado.startswith("Bearer "):
        raise PermissionError("Falta el token")
    try:
        datos = jwt.decode(
            encabezado.removeprefix("Bearer ").strip(),
            secreto(),
            algorithms=["HS256"],
        )
        company_user_id = int(datos["companyUserId"])
        company_id = int(datos["companyId"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise PermissionError("El token no es valido")

    membresia = db.get(CompanyUserModel, company_user_id)
    if membresia is None or not membresia.is_active:
        raise PermissionError("La membresia no existe o no esta activa")
    if membresia.company_id != company_id:
        raise PermissionError("El token no corresponde a esa empresa")
    return company_user_id
