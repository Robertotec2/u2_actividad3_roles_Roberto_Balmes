from models import RoleModel, PermissionModel, RolePermissionModel

PREFIJOS = {
    "COMPANY_USERS": "company.users.",
    "ACCOUNTS": "accounts.",
    "CONCEPTS": "concepts.",
    "TRANSACTIONS": "transactions.",
    "ROLES": "roles.",
}


def validar_propuesta(db, role_id, permission_ids):
    try:
        rid = int(role_id)
    except (TypeError, ValueError):
        raise ValueError(f"El id de rol {role_id} no es valido")
    rol = db.get(RoleModel, rid)
    if rol is None:
        raise ValueError(f"El rol {rid} no existe")
    if not rol.is_active:
        raise ValueError(f"El rol {rol.code} esta inactivo")
    if rol.code == "ADMINISTRADOR":
        raise ValueError("No se permite cambiar la lista de ADMINISTRADOR en este laboratorio")

    ids = []
    for pid in permission_ids:
        try:
            ids.append(int(pid))
        except (TypeError, ValueError):
            raise ValueError(f"El id de permiso {pid} no es valido")

    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    if repetidos:
        raise ValueError(f"Hay ids de permiso repetidos: {repetidos}")

    encontrados = {p.id: p for p in db.query(PermissionModel).filter(PermissionModel.id.in_(ids)).all()} if ids else {}
    faltan = [i for i in ids if i not in encontrados]
    if faltan:
        raise ValueError(f"Estos permisos no existen: {faltan}")
    inactivos = sorted(p.code for p in encontrados.values() if not p.is_active)
    if inactivos:
        raise ValueError(f"Estos permisos estan inactivos en el catalogo: {inactivos}")

    return rol, list(encontrados.values())


def calcular_plan(db, rol, deseados):
    activos = (
        db.query(PermissionModel)
        .join(RolePermissionModel, RolePermissionModel.permission_id == PermissionModel.id)
        .filter(RolePermissionModel.role_id == rol.id, RolePermissionModel.is_active.is_(True))
        .all()
    )
    ids_activos = {p.id for p in activos}
    ids_deseados = {p.id for p in deseados}

    def por_codigo(lista):
        return sorted(lista, key=lambda p: p.code)

    return {
        "role": rol,
        "current": por_codigo(activos),
        "to_activate": por_codigo(p for p in deseados if p.id not in ids_activos),
        "to_deactivate": por_codigo(p for p in activos if p.id not in ids_deseados),
        "unchanged": por_codigo(p for p in activos if p.id in ids_deseados),
        "final_count": len(deseados),
    }


def escribir_plan(db, plan):
    rol = plan["role"]
    for p in plan["to_activate"]:
        rp = db.query(RolePermissionModel).filter(
            RolePermissionModel.role_id == rol.id, RolePermissionModel.permission_id == p.id
        ).first()
        if rp:
            rp.is_active = True
        else:
            db.add(RolePermissionModel(role_id=rol.id, permission_id=p.id, is_active=True))
    for p in plan["to_deactivate"]:
        db.query(RolePermissionModel).filter(
            RolePermissionModel.role_id == rol.id, RolePermissionModel.permission_id == p.id
        ).update({"is_active": False})
    db.flush()


def aplicar_lista(db, role_id, permission_ids):
    rol, deseados = validar_propuesta(db, role_id, permission_ids)
    plan = calcular_plan(db, rol, deseados)
    if plan["to_activate"] or plan["to_deactivate"]:
        escribir_plan(db, plan)
    db.commit()
    return plan
