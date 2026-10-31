-- Actividad 5 - consultas de verificacion

-- Relaciones rol-permiso con su estado y el del catalogo
SELECT rp.id AS relacion_id, r.code AS rol, p.code AS permiso,
       rp.is_active AS relacion_activa, p.is_active AS permiso_activo
FROM role_permissions rp
JOIN roles r ON r.id = rp.role_id
JOIN permissions p ON p.id = rp.permission_id
ORDER BY r.code, p.code;

-- Parejas repetidas (debe dar cero filas)
SELECT role_id, permission_id, COUNT(*) AS repeticiones
FROM role_permissions
GROUP BY role_id, permission_id
HAVING COUNT(*) > 1;

-- Catalogo sin duplicados (4 roles y 10 permisos)
SELECT COUNT(*) AS roles FROM roles;
SELECT COUNT(*) AS permisos FROM permissions;

-- Membresia real de Ana e id de CAPTURISTA
SELECT cu.id AS company_user_id, u.name, cu.company_id
FROM company_users cu JOIN users u ON u.id = cu.user_id
WHERE u.name = 'Ana';
SELECT id, code FROM roles WHERE code = 'CAPTURISTA';

-- E06: preparacion y restauracion de estados inactivos
-- Rol inactivo
UPDATE roles SET is_active = 0 WHERE code = 'CONSULTA';
UPDATE roles SET is_active = 1 WHERE code = 'CONSULTA';
-- Permiso inactivo
UPDATE permissions SET is_active = 0 WHERE code = 'concepts.write';
UPDATE permissions SET is_active = 1 WHERE code = 'concepts.write';
