# app/db/queries.py
from typing import List, Dict, Any, Callable
from app.db.connection import get_db_connection, DatabaseConnection
from app.core.exceptions import DatabaseError
import pyodbc
import logging

logger = logging.getLogger(__name__)

def execute_query(query: str, params: tuple = (), connection_type: DatabaseConnection = DatabaseConnection.DEFAULT) -> List[Dict[str, Any]]:
    with get_db_connection(connection_type) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error en execute_query: {str(e)}")
            raise DatabaseError(status_code=500, detail=f"Error en la consulta: {str(e)}")
        finally:
            cursor.close()

def execute_auth_query(query: str, params: tuple = ()) -> Dict[str, Any]:
    """
    Ejecuta una consulta específica para autenticación y retorna un único registro.
    Siempre usa la conexión DEFAULT ya que la autenticación está en la BD principal.
    """
    with get_db_connection(DatabaseConnection.DEFAULT) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)

            if cursor.description is None:
                return None

            columns = [column[0] for column in cursor.description]
            row = cursor.fetchone()

            if row:
                return dict(zip(columns, row))
            return None

        except Exception as e:
            logger.error(f"Error en execute_auth_query: {str(e)}")
            raise DatabaseError(status_code=500, detail=f"Error en la autenticación: {str(e)}")
        finally:
            if cursor:
                cursor.close()

def execute_insert(query: str, params: tuple = (), connection_type: DatabaseConnection = DatabaseConnection.DEFAULT) -> Dict[str, Any]:
    """
    Ejecuta una sentencia INSERT y retorna:
      - Los datos retornados por OUTPUT si existen
      - Siempre incluye 'rows_affected' en la respuesta
    """
    with get_db_connection(connection_type) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)

            # Verificar OUTPUT
            if cursor.description:  
                columns = [column[0] for column in cursor.description]
                output_data = cursor.fetchone()
                result = dict(zip(columns, output_data)) if output_data else {}
            else:
                result = {}

            # Importante: filas afectadas
            rows_affected = cursor.rowcount
            result["rows_affected"] = rows_affected

            conn.commit()
            logger.info(f"Inserción exitosa, filas afectadas: {rows_affected}")
            return result

        except Exception as e:
            conn.rollback()
            logger.error(f"Error en execute_insert: {str(e)}")
            raise DatabaseError(
                status_code=500,
                detail=f"Error en la inserción: {str(e)}"
            )
        finally:
            cursor.close()                

def execute_update(query: str, params: tuple = (), connection_type: DatabaseConnection = DatabaseConnection.DEFAULT) -> Dict[str, Any]:
    with get_db_connection(connection_type) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            # Obtener número de filas afectadas
            rows_affected = cursor.rowcount
            
            # Si hay OUTPUT, obtener los datos
            if cursor.description:
                columns = [column[0] for column in cursor.description]
                output_data = cursor.fetchone()
                result = dict(zip(columns, output_data)) if output_data else {}
            else:
                result = {}
            
            conn.commit()
            
            # CAMBIO CLAVE: Siempre incluir rows_affected en la respuesta
            result['rows_affected'] = rows_affected
            
            logger.info(f"Actualización exitosa, filas afectadas: {rows_affected}")
            return result

        except Exception as e:
            conn.rollback()
            logger.error(f"Error en execute_update: {str(e)}")
            raise DatabaseError(
                status_code=500,
                detail=f"Error en la actualización: {str(e)}"
            )
        finally:
            cursor.close()

def execute_procedure(procedure_name: str, connection_type: DatabaseConnection = DatabaseConnection.DEFAULT) -> List[Dict[str, Any]]:
    with get_db_connection(connection_type) as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(f"EXEC {procedure_name}")

            results = []
            while True:
                if cursor.description:
                    columns = [column[0] for column in cursor.description]
                    results.extend([dict(zip(columns, row)) for row in cursor.fetchall()])
                if not cursor.nextset():
                    break
            return results
        except Exception as e:
            logger.error(f"Error en execute_procedure: {str(e)}")
            raise DatabaseError(status_code=500, detail=f"Error en el procedimiento: {str(e)}")
        finally:
            cursor.close()

def execute_procedure_params(
    procedure_name: str,
    params: dict,
    connection_type: DatabaseConnection = DatabaseConnection.DEFAULT
) -> List[Dict[str, Any]]:
    with get_db_connection(connection_type) as conn:
        try:
            cursor = conn.cursor()
            param_str = ", ".join([f"@{key} = ?" for key in params.keys()])
            query = f"EXEC {procedure_name} {param_str}"

            cursor.execute(query, tuple(params.values()))

            results = []
            while True:
                if cursor.description:
                    columns = [column[0] for column in cursor.description]
                    results.extend([dict(zip(columns, row)) for row in cursor.fetchall()])
                if not cursor.nextset():
                    break
            return results
        except Exception as e:
            logger.error(f"Error en execute_procedure_params: {str(e)}")
            raise DatabaseError(status_code=500, detail=f"Error en el procedimiento: {str(e)}")
        finally:
            cursor.close()

def execute_transaction(
    operations_func: Callable[[pyodbc.Cursor], None],
    connection_type: DatabaseConnection = DatabaseConnection.DEFAULT
) -> None:
    """
    Ejecuta operaciones de BD en una transacción.
    Maneja errores de conexión y operación de pyodbc.
    """
    conn = None
    cursor = None
    try:
        with get_db_connection(connection_type) as conn:
            cursor = conn.cursor()
            operations_func(cursor)
            conn.commit()
            logger.debug("Transacción completada exitosamente.")

    except pyodbc.Error as db_err:
        logger.error(f"Error de base de datos (pyodbc) en transacción: {db_err}", exc_info=True)
        raise DatabaseError(status_code=500, detail=f"Error DB en transacción: {str(db_err)}")

    except Exception as e:
        logger.error(f"Error inesperado (no pyodbc) en transacción: {e}", exc_info=True)
        raise DatabaseError(status_code=500, detail=f"Error inesperado en transacción: {str(e)}")

# Consulta para obtener usuarios paginados con sus roles, filtrando eliminados y buscando
SELECT_USUARIOS_PAGINATED = """
WITH UserRoles AS (
    SELECT
        u.usuario_id,
        u.nombre_usuario,
        u.correo,
        u.nombre,
        u.apellido,
        u.es_activo,
        u.correo_confirmado,
        u.fecha_creacion,
        u.fecha_ultimo_acceso,
        u.fecha_actualizacion,
        r.rol_id,
        r.nombre AS nombre_rol
        -- Añade aquí otros campos de 'usuario' o 'rol' que necesites
    FROM usuario u
    LEFT JOIN usuario_rol ur ON u.usuario_id = ur.usuario_id AND ur.es_activo = 1
    LEFT JOIN rol r ON ur.rol_id = r.rol_id AND r.es_activo = 1
    WHERE
        u.es_eliminado = 0
        AND (? IS NULL OR (
            u.nombre_usuario LIKE ? OR
            u.correo LIKE ? OR
            u.nombre LIKE ? OR
            u.apellido LIKE ?
        ))
)
SELECT * FROM UserRoles
ORDER BY usuario_id -- O el campo por el que prefieras ordenar por defecto
OFFSET ? ROWS FETCH NEXT ? ROWS ONLY;
"""

# Consulta para contar el total de usuarios que coinciden con la búsqueda y no están eliminados
COUNT_USUARIOS_PAGINATED = """
SELECT COUNT(DISTINCT u.usuario_id)
FROM usuario u
WHERE
    u.es_eliminado = 0
    AND (? IS NULL OR (
        u.nombre_usuario LIKE ? OR
        u.correo LIKE ? OR
        u.nombre LIKE ? OR
        u.apellido LIKE ?
    ));
"""

# --- Consultas de Roles (Existentes - SIN CAMBIOS) ---
# (Asumiendo que tienes aquí tus queries SELECT_ROL_BY_ID, INSERT_ROL, etc.)
# Si no las tienes, deberías añadirlas aquí. Por ejemplo:
SELECT_ROL_BY_ID = "SELECT rol_id, nombre, descripcion, es_activo, fecha_creacion FROM dbo.rol WHERE rol_id = ? AND es_activo = 1"
SELECT_ALL_ROLES = "SELECT rol_id, nombre, descripcion, es_activo, fecha_creacion FROM dbo.rol WHERE es_activo = 1 ORDER BY nombre"
INSERT_ROL = "INSERT INTO dbo.rol (nombre, descripcion, es_activo) OUTPUT INSERTED.rol_id, INSERTED.nombre, INSERTED.descripcion, INSERTED.es_activo, INSERTED.fecha_creacion VALUES (?, ?, ?)"
UPDATE_ROL = "UPDATE dbo.rol SET nombre = ?, descripcion = ?, es_activo = ? OUTPUT INSERTED.rol_id, INSERTED.nombre, INSERTED.descripcion, INSERTED.es_activo, INSERTED.fecha_creacion WHERE rol_id = ?"
# Nota: DEACTIVATE_ROL podría ser un caso especial de UPDATE_ROL o una query separada
DEACTIVATE_ROL = """
    UPDATE dbo.rol
    SET
        es_activo = 0
    OUTPUT
        INSERTED.rol_id,
        INSERTED.nombre,
        INSERTED.descripcion,
        INSERTED.es_activo,
        INSERTED.fecha_creacion
    WHERE
        rol_id = ?
        AND es_activo = 1;  -- Solo desactivar si está activo
"""
REACTIVATE_ROL = """
    UPDATE dbo.rol
    SET
        es_activo = 1
    OUTPUT
        INSERTED.rol_id,
        INSERTED.nombre,
        INSERTED.descripcion,
        INSERTED.es_activo,
        INSERTED.fecha_creacion
    WHERE
        rol_id = ?
        AND es_activo = 0;  -- Solo reactivar si está inactivo
"""
CHECK_ROL_NAME_EXISTS = "SELECT rol_id FROM dbo.rol WHERE LOWER(nombre) = LOWER(?) AND rol_id != ?"


# --- NUEVAS QUERIES PARA PAGINACIÓN DE ROLES ---
COUNT_ROLES_PAGINATED = """
    SELECT COUNT(rol_id) as total -- Añadir alias 'total' para consistencia
    FROM dbo.rol
    WHERE (? IS NULL OR (
        LOWER(nombre) LIKE LOWER(?) OR
        LOWER(descripcion) LIKE LOWER(?)
    ));
    -- Nota: No filtra por es_activo aquí para mostrar todos en mantenimiento
    -- Usamos LOWER() para búsqueda insensible a mayúsculas/minúsculas
"""

SELECT_ROLES_PAGINATED = """
    SELECT
        rol_id, nombre, descripcion, es_activo, fecha_creacion
        -- , fecha_actualizacion -- Descomentar si existe y la quieres mostrar
    FROM
        dbo.rol
    WHERE (? IS NULL OR (
        LOWER(nombre) LIKE LOWER(?) OR
        LOWER(descripcion) LIKE LOWER(?)
    ))
    ORDER BY
        rol_id -- O el campo que prefieras (ej. rol_id)
    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY;
    -- Nota: No filtra por es_activo aquí
    -- Usamos LOWER() para búsqueda insensible a mayúsculas/minúsculas
"""
# --- FIN NUEVAS QUERIES ---

# --- NUEVA CONSULTA PARA MENUS (ADMIN) ---
# Llama a la nueva Stored Procedure que obtiene TODOS los menús
GET_ALL_MENUS_ADMIN = "sp_GetAllMenuItemsAdmin;"


# --- NUEVAS CONSULTAS PARA PERMISOS (RolMenuPermiso) ---

# Selecciona todos los permisos asignados a un rol específico
SELECT_PERMISOS_POR_ROL = """
    SELECT rol_menu_id, rol_id, menu_id, puede_ver, puede_editar, puede_eliminar
    FROM rol_menu_permiso
    WHERE rol_id = ?;
"""

# Elimina TODOS los permisos asociados a un rol específico.
# Se usa antes de insertar los nuevos permisos actualizados.
DELETE_PERMISOS_POR_ROL = """
    DELETE FROM rol_menu_permiso
    WHERE rol_id = ?;
"""

# Inserta un nuevo registro de permiso para un rol y un menú.
# Los parámetros serán (rol_id, menu_id, puede_ver, puede_editar, puede_eliminar)
INSERT_PERMISO_ROL = """
    INSERT INTO rol_menu_permiso (rol_id, menu_id, puede_ver, puede_editar, puede_eliminar)
    VALUES (?, ?, ?, ?, ?);
"""

# --- FIN DE NUEVAS CONSULTAS ---

# --- NUEVAS QUERIES PARA MANTENIMIENTO DE MENÚ ---

INSERT_MENU = """
    INSERT INTO menu (nombre, icono, ruta, padre_menu_id, orden, area_id, es_activo)
    OUTPUT INSERTED.menu_id, INSERTED.nombre, INSERTED.icono, INSERTED.ruta,
           INSERTED.padre_menu_id, INSERTED.orden, INSERTED.es_activo, INSERTED.area_id,
           INSERTED.fecha_creacion -- Añadir fecha_creacion si la quieres devolver
           -- , a.nombre as area_nombre -- No podemos hacer JOIN fácil en INSERT OUTPUT
    VALUES (?, ?, ?, ?, ?, ?, ?);
"""

# Selecciona un menú por ID, incluyendo el nombre del área
SELECT_MENU_BY_ID = """
    SELECT m.menu_id, m.nombre, m.icono, m.ruta, m.padre_menu_id, m.orden,
           m.es_activo, m.fecha_creacion, m.area_id, a.nombre as area_nombre
    FROM menu m
    LEFT JOIN area_menu a ON m.area_id = a.area_id
    WHERE m.menu_id = ?;
"""

# Actualiza un menú. La lógica para construir SET se hará en el servicio.
# Esta es una plantilla base, necesitaremos construir la query dinámicamente.
# O una query que actualice todos los campos opcionales usando COALESCE o ISNULL.
# Ejemplo con COALESCE (SQL Server):
UPDATE_MENU_TEMPLATE = """
    UPDATE menu
    SET
        nombre = COALESCE(?, nombre),
        icono = COALESCE(?, icono),
        ruta = COALESCE(?, ruta),
        padre_menu_id = COALESCE(?, padre_menu_id),
        orden = COALESCE(?, orden),
        area_id = COALESCE(?, area_id),
        es_activo = COALESCE(?, es_activo)
    OUTPUT INSERTED.menu_id, INSERTED.nombre, INSERTED.icono, INSERTED.ruta,
           INSERTED.padre_menu_id, INSERTED.orden, INSERTED.es_activo, INSERTED.area_id,
           INSERTED.fecha_creacion -- Añadir fecha_creacion si la quieres devolver
           -- , (SELECT nombre FROM area_menu WHERE area_id = INSERTED.area_id) as area_nombre -- Subconsulta para nombre de área
    WHERE menu_id = ?;
"""
# Nota: El orden de los COALESCE debe coincidir con el orden de los parámetros opcionales en el servicio.

# Desactiva un menú (Borrado Lógico)
DEACTIVATE_MENU = """
    UPDATE menu
    SET es_activo = 0
    OUTPUT INSERTED.menu_id, INSERTED.es_activo
    WHERE menu_id = ? AND es_activo = 1;
"""

# Reactiva un menú (Opcional pero útil)
REACTIVATE_MENU = """
    UPDATE menu
    SET es_activo = 1
    OUTPUT INSERTED.menu_id, INSERTED.es_activo
    WHERE menu_id = ? AND es_activo = 0;
"""

# Verifica si un menú existe
CHECK_MENU_EXISTS = "SELECT 1 FROM menu WHERE menu_id = ?"

# Verifica si un área existe
CHECK_AREA_EXISTS = "SELECT 1 FROM area_menu WHERE area_id = ?"

# Stored Procedure para obtener todos los menús (Admin - ya definido)
GET_ALL_MENUS_ADMIN = "sp_GetAllMenuItemsAdmin" # Asegúrate que este SP devuelva area_id y area_nombre

# --- QUERIES PARA AREA_MENU (CON PAGINACIÓN Y BÚSQUEDA) ---

GET_AREAS_PAGINATED_QUERY = """
    SELECT
        area_id, nombre, descripcion, icono, es_activo, fecha_creacion
    FROM
        area_menu -- Nombre de tabla correcto
    WHERE
        (? IS NULL OR LOWER(nombre) LIKE LOWER(?) OR LOWER(descripcion) LIKE LOWER(?))
    ORDER BY
        area_id ASC
    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY; -- Sintaxis SQL Server
"""

COUNT_AREAS_QUERY = """
    SELECT
        COUNT(*) as total_count
    FROM
        area_menu -- Nombre de tabla correcto
    WHERE
        (? IS NULL OR LOWER(nombre) LIKE LOWER(?) OR LOWER(descripcion) LIKE LOWER(?));
"""

GET_AREA_BY_ID_QUERY = "SELECT area_id, nombre, descripcion, icono, es_activo, fecha_creacion FROM area_menu WHERE area_id = ?;"

CHECK_AREA_EXISTS_BY_NAME_QUERY = "SELECT COUNT(*) as count FROM area_menu WHERE LOWER(nombre) = LOWER(?) AND area_id != ?;"

CREATE_AREA_QUERY = """
INSERT INTO area_menu (nombre, descripcion, icono, es_activo)
OUTPUT INSERTED.area_id, INSERTED.nombre, INSERTED.descripcion, INSERTED.icono, INSERTED.es_activo, INSERTED.fecha_creacion
VALUES (?, ?, ?, ?);
"""

UPDATE_AREA_BASE_QUERY_TEMPLATE = "UPDATE area_menu SET {fields} OUTPUT INSERTED.* WHERE area_id = ?;" # Plantilla para actualizar

TOGGLE_AREA_STATUS_QUERY = """
UPDATE area_menu SET es_activo = ?
OUTPUT INSERTED.area_id, INSERTED.nombre, INSERTED.descripcion, INSERTED.icono, INSERTED.es_activo, INSERTED.fecha_creacion
WHERE area_id = ?;
""" # Para activar/desactivar

GET_ACTIVE_AREAS_SIMPLE_LIST_QUERY = """
SELECT
    area_id,
    nombre
FROM
    area_menu -- Confirma que 'area_menu' es el nombre correcto de tu tabla
WHERE
    es_activo = 1 -- O = TRUE, dependiendo de tu SGBD
ORDER BY
    nombre ASC;
"""

GET_MENUS_BY_AREA_FOR_TREE_QUERY = """
SELECT
    m.menu_id,
    m.nombre,
    m.icono,
    m.ruta, -- Asegúrate que el nombre de columna sea 'ruta' o 'url' según tu tabla
    m.padre_menu_id,
    m.orden,
    m.es_activo,
    m.area_id,
    a.nombre as area_nombre -- Opcional: si quieres mostrar el nombre del área
    -- No incluyas 'level' aquí, build_menu_tree lo calcula si es necesario
FROM
    menu m -- Confirma el nombre de tu tabla de menú
LEFT JOIN
    area_menu a ON m.area_id = a.area_id -- Confirma nombre tabla área y JOIN
WHERE
    m.area_id = ? -- Parámetro para el ID del área
ORDER BY
    m.padre_menu_id ASC, -- Agrupa hijos bajo sus padres
    m.orden ASC; -- Ordena los hermanos entre sí
"""

# --- Queries originales que podrían quedar obsoletas ---
# GET_ALL_AREAS_ADMIN = "SELECT area_id, nombre, descripcion, icono, es_activo, fecha_creacion FROM area_menu ORDER BY nombre;"
# GET_ACTIVE_AREAS = "SELECT area_id, nombre, descripcion, icono, es_activo, fecha_creacion FROM area_menu WHERE es_activo = 1 ORDER BY nombre;"
# SELECT_AREA_BY_ID = "SELECT area_id, nombre, descripcion, icono, es_activo, fecha_creacion FROM area_menu WHERE area_id = ?;" # Reemplazada por GET_AREA_BY_ID_QUERY
# SELECT_AREA_BY_NAME = "SELECT area_id, nombre FROM area_menu WHERE nombre = ?;" # Reemplazada por CHECK_AREA_EXISTS_BY_NAME_QUERY
# INSERT_AREA = """...""" # Reemplazada por CREATE_AREA_QUERY
# UPDATE_AREA_TEMPLATE = "..." # Reemplazada por UPDATE_AREA_BASE_QUERY_TEMPLATE
# DEACTIVATE_AREA = "..." # Reemplazada por TOGGLE_AREA_STATUS_QUERY
# REACTIVATE_AREA = "..." # Reemplazada por TOGGLE_AREA_STATUS_QUERY

GET_MAX_ORDEN_FOR_SIBLINGS = """
    SELECT MAX(orden) as max_orden
    FROM menu
    WHERE area_id = ? AND padre_menu_id = ?;
"""

# NUEVA QUERY: Obtiene el máximo valor de 'orden' para los elementos raíz de un área
GET_MAX_ORDEN_FOR_ROOT = """
    SELECT MAX(orden) as max_orden
    FROM menu
    WHERE area_id = ? AND padre_menu_id IS NULL;
"""