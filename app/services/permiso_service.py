# app/services/permiso_service.py

from typing import Dict, List, Optional, Any
import logging

# 🗄️ IMPORTACIONES DE BASE DE DATOS
from app.db.queries import execute_query, execute_insert, execute_update

# 🚨 EXCEPCIONES - Nuevo sistema de manejo de errores
from app.core.exceptions import (
    ValidationError, NotFoundError, ServiceError, DatabaseError
)

# 🏗️ BASE SERVICE - Clase base para manejo consistente de errores
from app.services.base_service import BaseService

# 👥 SERVICIOS RELACIONADOS
from app.services.rol_service import RolService
from app.services.menu_service import MenuService

logger = logging.getLogger(__name__)

class PermisoService(BaseService):
    """
    Servicio para gestión de permisos de roles sobre menús.
    
    ⚠️ IMPORTANTE: Este servicio maneja operaciones críticas relacionadas con:
    - Asignación y actualización de permisos de roles sobre menús
    - Consulta de permisos existentes
    - Revocación de permisos
    
    CARACTERÍSTICAS PRINCIPALES:
    - Herencia de BaseService para manejo automático de errores
    - Validaciones robustas de existencia de roles y menús
    - Operaciones atómicas para asignación/actualización
    - Logging detallado para auditoría de seguridad
    """

    @staticmethod
    @BaseService.handle_service_errors
    async def _validar_rol_y_menu(rol_id: int, menu_id: int) -> None:
        """
        Valida la existencia del rol y el menú.
        
        🛡️ VALIDACIÓN DE INTEGRIDAD REFERENCIAL:
        - Verifica que el rol exista y esté activo
        - Verifica que el menú exista y esté activo
        - Previene asignaciones a entidades inexistentes
        
        Args:
            rol_id: ID del rol a validar
            menu_id: ID del menú a validar
            
        Raises:
            NotFoundError: Si el rol o el menú no existen
            ServiceError: Si hay errores en la validación
        """
        try:
            # 👤 VALIDAR ROL
            rol = await RolService.obtener_rol_por_id(rol_id)
            if not rol:
                raise NotFoundError(
                    detail=f"Rol con ID {rol_id} no encontrado.",
                    internal_code="ROLE_NOT_FOUND"
                )

            # 📋 VALIDAR MENÚ
            menu = await MenuService.obtener_menu_por_id(menu_id)
            if not menu:
                raise NotFoundError(
                    detail=f"Menú con ID {menu_id} no encontrado.",
                    internal_code="MENU_NOT_FOUND"
                )

            logger.debug(f"Validación exitosa - Rol ID: {rol_id}, Menú ID: {menu_id}")

        except (NotFoundError, ServiceError):
            # 🔄 RE-LANZAR ERRORES ESPECÍFICOS
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD en _validar_rol_y_menu: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al validar rol y menú",
                internal_code="ROLE_MENU_VALIDATION_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado en _validar_rol_y_menu: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al validar rol y menú",
                internal_code="ROLE_MENU_VALIDATION_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def asignar_o_actualizar_permiso(
        rol_id: int,
        menu_id: int,
        puede_ver: Optional[bool] = None,
        puede_editar: Optional[bool] = None,
        puede_eliminar: Optional[bool] = None
    ) -> Dict:
        """
        Asigna o actualiza los permisos de un rol sobre un menú.
        
        🔄 COMPORTAMIENTO INTELIGENTE:
        - Si el permiso no existe, lo crea
        - Si el permiso existe, lo actualiza
        - Solo actualiza los campos proporcionados
        
        Args:
            rol_id: ID del rol
            menu_id: ID del menú
            puede_ver: Permiso para ver (opcional)
            puede_editar: Permiso para editar (opcional)
            puede_eliminar: Permiso para eliminar (opcional)
            
        Returns:
            Dict: Permiso asignado o actualizado
            
        Raises:
            NotFoundError: Si el rol o menú no existen
            ValidationError: Si no se proporciona al menos un permiso
            ServiceError: Si la operación falla
        """
        logger.info(f"Intentando asignar/actualizar permiso - Rol: {rol_id}, Menú: {menu_id}")

        try:
            # 1. 🛡️ VALIDAR ROL Y MENÚ
            await PermisoService._validar_rol_y_menu(rol_id, menu_id)

            # 2. 🚫 VALIDAR AL MENOS UN PERMISO PROPORCIONADO
            permiso_data = {}
            if puede_ver is not None:
                permiso_data['puede_ver'] = puede_ver
            if puede_editar is not None:
                permiso_data['puede_editar'] = puede_editar
            if puede_eliminar is not None:
                permiso_data['puede_eliminar'] = puede_eliminar

            if not permiso_data:
                raise ValidationError(
                    detail="Debe proporcionar al menos un permiso (ver, editar, eliminar).",
                    internal_code="NO_PERMISSIONS_PROVIDED"
                )

            # 3. 🔍 VERIFICAR SI EL PERMISO YA EXISTE
            check_query = """
            SELECT rol_menu_id, puede_ver, puede_editar, puede_eliminar
            FROM rol_menu_permiso
            WHERE rol_id = ? AND menu_id = ?
            """
            existing_perm = execute_query(check_query, (rol_id, menu_id))

            if existing_perm:
                # 🟡 ACTUALIZAR PERMISO EXISTENTE
                perm_id = existing_perm[0]['rol_menu_id']
                current_perms = existing_perm[0]
                logger.info(f"Actualizando permiso existente ID {perm_id}")

                update_parts = []
                params = []
                # 🛠️ CONSTRUIR SET DINÁMICAMENTE
                for key, value in permiso_data.items():
                    # 🔄 Actualizar solo si el valor es diferente al actual
                    if value != current_perms.get(key):
                        update_parts.append(f"{key} = ?")
                        params.append(value)

                # ✅ VERIFICAR SI HAY CAMBIOS REALES
                if not update_parts:
                    logger.info(f"No hay cambios en los permisos para ID {perm_id}")
                    get_query = """
                    SELECT rol_menu_id, rol_id, menu_id, puede_ver, puede_editar, puede_eliminar
                    FROM rol_menu_permiso WHERE rol_menu_id = ?
                    """
                    return execute_query(get_query, (perm_id,))[0]

                params.append(perm_id)  # Añadir ID para el WHERE

                update_query = f"""
                UPDATE rol_menu_permiso
                SET {', '.join(update_parts)}
                OUTPUT INSERTED.rol_menu_id, INSERTED.rol_id, INSERTED.menu_id,
                       INSERTED.puede_ver, INSERTED.puede_editar, INSERTED.puede_eliminar
                WHERE rol_menu_id = ?
                """
                result = execute_update(update_query, tuple(params))
                if not result:
                    raise ServiceError(
                        status_code=500,
                        detail="Error al actualizar el permiso.",
                        internal_code="PERMISSION_UPDATE_FAILED"
                    )
                logger.info(f"Permiso ID {perm_id} actualizado exitosamente")
                return result

            else:
                # 🟢 CREAR NUEVO PERMISO
                logger.info(f"🟢 Creando nuevo permiso - Rol: {rol_id}, Menú: {menu_id}")

                # 🎯 ESTABLECER VALORES POR DEFECTO
                final_puede_ver = permiso_data.get('puede_ver', False)
                final_puede_editar = permiso_data.get('puede_editar', False)
                final_puede_eliminar = permiso_data.get('puede_eliminar', False)

                insert_query = """
                INSERT INTO rol_menu_permiso (rol_id, menu_id, puede_ver, puede_editar, puede_eliminar)
                OUTPUT INSERTED.rol_menu_id, INSERTED.rol_id, INSERTED.menu_id,
                       INSERTED.puede_ver, INSERTED.puede_editar, INSERTED.puede_eliminar
                VALUES (?, ?, ?, ?, ?)
                """
                params = (rol_id, menu_id, final_puede_ver, final_puede_editar, final_puede_eliminar)
                result = execute_insert(insert_query, params)
                if not result:
                    raise ServiceError(
                        status_code=500,
                        detail="Error al crear el permiso.",
                        internal_code="PERMISSION_CREATION_FAILED"
                    )
                logger.info(f"Permiso creado exitosamente con ID {result['rol_menu_id']}")
                return result

        except (ValidationError, NotFoundError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD en asignar_o_actualizar_permiso: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al gestionar permiso",
                internal_code="PERMISSION_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado en asignar_o_actualizar_permiso: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al gestionar permiso",
                internal_code="PERMISSION_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def obtener_permisos_por_rol(rol_id: int) -> List[Dict]:
        """
        Obtiene todos los permisos asignados a un rol específico.
        
        📋 LISTA COMPLETA DE PERMISOS:
        - Incluye detalles del menú asociado
        - Ordenado por menú para consistencia
        - Retorna lista vacía si no hay permisos
        
        Args:
            rol_id: ID del rol cuyos permisos se quieren obtener
            
        Returns:
            List[Dict]: Lista de permisos del rol con detalles del menú
            
        Raises:
            ServiceError: Si hay errores en la consulta
        """
        try:
            # 🎯 VALIDAR QUE EL ROL EXISTE (OPCIONAL PERO RECOMENDADO)
            rol = await RolService.obtener_rol_por_id(rol_id)
            if not rol:
                logger.warning(f"Intento de obtener permisos para rol inexistente ID {rol_id}")
                return []  # 📭 Retornar lista vacía en lugar de error

            query = """
            SELECT
                p.rol_menu_id, p.rol_id, p.menu_id,
                p.puede_ver, p.puede_editar, p.puede_eliminar,
                m.nombre AS menu_nombre, m.ruta AS menu_url, m.icono AS menu_icono
            FROM rol_menu_permiso p
            INNER JOIN menu m ON p.menu_id = m.menu_id
            WHERE p.rol_id = ?
            ORDER BY m.orden;
            """
            permisos = execute_query(query, (rol_id,))
            logger.debug(f"Obtenidos {len(permisos)} permisos para rol ID {rol_id}")
            return permisos

        except DatabaseError as db_err:
            logger.error(f"Error de BD en obtener_permisos_por_rol: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener permisos del rol",
                internal_code="ROLE_PERMISSIONS_RETRIEVAL_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado en obtener_permisos_por_rol: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al obtener permisos del rol",
                internal_code="ROLE_PERMISSIONS_RETRIEVAL_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def obtener_permiso_especifico(rol_id: int, menu_id: int) -> Optional[Dict]:
        """
        Obtiene el permiso específico de un rol sobre un menú.
        
        🔍 BÚSQUEDA PRECISA:
        - Retorna el permiso específico para el par rol-menú
        - Retorna None si no existe el permiso
        
        Args:
            rol_id: ID del rol
            menu_id: ID del menú
            
        Returns:
            Optional[Dict]: Permiso encontrado o None
            
        Raises:
            ServiceError: Si hay errores en la consulta
        """
        try:
            query = """
            SELECT rol_menu_id, rol_id, menu_id, puede_ver, puede_editar, puede_eliminar
            FROM rol_menu_permiso
            WHERE rol_id = ? AND menu_id = ?
            """
            resultados = execute_query(query, (rol_id, menu_id))
            if not resultados:
                logger.debug(f"Permiso no encontrado - Rol: {rol_id}, Menú: {menu_id}")
                return None
            return resultados[0]

        except DatabaseError as db_err:
            logger.error(f"Error de BD en obtener_permiso_especifico: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al obtener permiso específico",
                internal_code="SPECIFIC_PERMISSION_RETRIEVAL_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado en obtener_permiso_especifico: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al obtener permiso específico",
                internal_code="SPECIFIC_PERMISSION_RETRIEVAL_UNEXPECTED_ERROR"
            )

    @staticmethod
    @BaseService.handle_service_errors
    async def revocar_permiso(rol_id: int, menu_id: int) -> Dict:
        """
        Revoca (elimina) el permiso de un rol sobre un menú.
        
        🗑️ ELIMINACIÓN SEGURA:
        - Verifica que el permiso exista antes de eliminar
        - Retorna mensaje de confirmación
        - Operación irreversible
        
        Args:
            rol_id: ID del rol
            menu_id: ID del menú
            
        Returns:
            Dict: Mensaje de confirmación
            
        Raises:
            NotFoundError: Si el permiso no existe
            ServiceError: Si la eliminación falla
        """
        try:
            # 1. 🔍 VERIFICAR EXISTENCIA DEL PERMISO
            permiso_existente = await PermisoService.obtener_permiso_especifico(rol_id, menu_id)
            if not permiso_existente:
                raise NotFoundError(
                    detail=f"No se encontró permiso para eliminar (Rol ID: {rol_id}, Menú ID: {menu_id}).",
                    internal_code="PERMISSION_NOT_FOUND"
                )

            # 2. 🗑️ EJECUTAR ELIMINACIÓN
            delete_query = """
            DELETE FROM rol_menu_permiso
            WHERE rol_id = ? AND menu_id = ?
            """
            # 📝 Usamos execute_update para operaciones DELETE
            result = execute_update(delete_query, (rol_id, menu_id))

            # ✅ VERIFICAR QUE SE ELIMINÓ AL MENOS UNA FILA
            if result.get('rows_affected', 0) == 0:
                raise ServiceError(
                    status_code=500,
                    detail="No se pudo eliminar el permiso.",
                    internal_code="PERMISSION_DELETION_FAILED"
                )

            logger.info(f"Permiso revocado exitosamente - Rol: {rol_id}, Menú: {menu_id}")
            return {"message": "Permiso revocado exitosamente"}

        except (ValidationError, NotFoundError):
            raise
        except DatabaseError as db_err:
            logger.error(f"Error de BD en revocar_permiso: {db_err.detail}")
            raise ServiceError(
                status_code=500,
                detail="Error de base de datos al revocar permiso",
                internal_code="PERMISSION_REVOCATION_DB_ERROR"
            )
        except Exception as e:
            logger.exception(f"Error inesperado en revocar_permiso: {str(e)}")
            raise ServiceError(
                status_code=500,
                detail="Error interno al revocar permiso",
                internal_code="PERMISSION_REVOCATION_UNEXPECTED_ERROR"
            )