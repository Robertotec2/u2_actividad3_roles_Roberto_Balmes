-- Actividad 5: una sola fila por pareja (role_id, permission_id).
-- main.py la aplica al arrancar si falta. Antes revisar que no haya duplicados:
SELECT role_id, permission_id, COUNT(*) AS repeticiones
FROM role_permissions
GROUP BY role_id, permission_id
HAVING COUNT(*) > 1;

ALTER TABLE role_permissions
  ADD CONSTRAINT uq_role_permission UNIQUE (role_id, permission_id);
